#pragma once

#include <algorithm>
#include <memory>
#include <string>
#include <wrl.h>

namespace webview {

// 仅接管显式使用 neutralino-popup: 名称的空白弹窗，其他弹窗保持默认行为。
class popup_window : public std::enable_shared_from_this<popup_window> {
    template<class T> using com_ptr = Microsoft::WRL::ComPtr<T>;
    HWND window_ = nullptr;
    bool attached_ = false;
    com_ptr<ICoreWebView2Controller> controller_;
    com_ptr<ICoreWebView2> view_;

    static LRESULT CALLBACK window_proc(HWND window, UINT message, WPARAM wparam, LPARAM lparam) {
        auto holder = reinterpret_cast<std::shared_ptr<popup_window>*>(GetWindowLongPtrW(window, GWLP_USERDATA));
        if (message == WM_NCCREATE) {
            holder = static_cast<std::shared_ptr<popup_window>*>(reinterpret_cast<CREATESTRUCTW*>(lparam)->lpCreateParams);
            SetWindowLongPtrW(window, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(holder));
            (*holder)->window_ = window;
            (*holder)->attached_ = true;
        }
        if (!holder) return DefWindowProcW(window, message, wparam, lparam);
        auto popup = *holder;
        switch (message) {
        case WM_SIZE:
            if (popup->controller_) {
                RECT bounds;
                GetClientRect(window, &bounds);
                popup->controller_->put_Bounds(bounds);
            }
            return 0;
        case WM_SETFOCUS:
            if (popup->controller_) popup->controller_->MoveFocus(COREWEBVIEW2_MOVE_FOCUS_REASON_PROGRAMMATIC);
            return 0;
        case WM_DPICHANGED:
            {
                const auto rect = reinterpret_cast<RECT*>(lparam);
                SetWindowPos(window, nullptr, rect->left, rect->top, rect->right - rect->left,
                    rect->bottom - rect->top, SWP_NOZORDER | SWP_NOACTIVATE);
            }
            return 0;
        case WM_CLOSE:
            // 由页面关闭流程触发卸载事件，保持 window.closed 和原有清理回调的语义。
            if (popup->view_ && SUCCEEDED(popup->view_->ExecuteScript(L"window.close()", nullptr))) return 0;
            break;
        case WM_NCDESTROY:
            SetWindowLongPtrW(window, GWLP_USERDATA, 0);
            popup->window_ = nullptr;
            if (popup->controller_) popup->controller_->Close();
            popup->view_.Reset();
            popup->controller_.Reset();
            delete holder;
            break;
        }
        return DefWindowProcW(window, message, wparam, lparam);
    }

    void initialize(ICoreWebView2Controller* controller, ICoreWebView2* source,
                    ICoreWebView2NewWindowRequestedEventArgs* request) {
        controller_ = controller;
        controller_->get_CoreWebView2(&view_);
        com_ptr<ICoreWebView2Settings> settings, source_settings;
        view_->get_Settings(&settings);
        source->get_Settings(&source_settings);
        BOOL enabled = FALSE;
        source_settings->get_AreDevToolsEnabled(&enabled);
        settings->put_AreDevToolsEnabled(enabled);
        settings->put_IsStatusBarEnabled(FALSE);
        RECT bounds;
        GetClientRect(window_, &bounds);
        controller_->put_Bounds(bounds);
        std::weak_ptr<popup_window> weak = shared_from_this();
        EventRegistrationToken token;
        view_->add_DocumentTitleChanged(Microsoft::WRL::Callback<ICoreWebView2DocumentTitleChangedEventHandler>(
            [weak](ICoreWebView2* sender, IUnknown*) -> HRESULT {
                if (auto popup = weak.lock()) {
                    LPWSTR title = nullptr;
                    if (SUCCEEDED(sender->get_DocumentTitle(&title))) {
                        SetWindowTextW(popup->window_, title);
                        CoTaskMemFree(title);
                    }
                }
                return S_OK;
            }).Get(), &token);
        view_->add_WindowCloseRequested(Microsoft::WRL::Callback<ICoreWebView2WindowCloseRequestedEventHandler>(
            [weak](ICoreWebView2*, IUnknown*) -> HRESULT {
                if (auto popup = weak.lock()) DestroyWindow(popup->window_);
                return S_OK;
            }).Get(), &token);
        if (FAILED(request->put_NewWindow(view_.Get()))) {
            DestroyWindow(window_);
            return;
        }
        ShowWindow(window_, SW_SHOW);
        controller_->put_IsVisible(TRUE);
        controller_->MoveFocus(COREWEBVIEW2_MOVE_FOCUS_REASON_PROGRAMMATIC);
    }

public:
    static void attach(ICoreWebView2* source, ICoreWebView2Environment* environment, HWND owner) {
        com_ptr<ICoreWebView2Environment> env = environment;
        EventRegistrationToken token;
        source->add_NewWindowRequested(Microsoft::WRL::Callback<ICoreWebView2NewWindowRequestedEventHandler>(
            [env, owner](ICoreWebView2* sender, ICoreWebView2NewWindowRequestedEventArgs* args) -> HRESULT {
                com_ptr<ICoreWebView2NewWindowRequestedEventArgs2> named;
                if (FAILED(args->QueryInterface(IID_PPV_ARGS(&named)))) return S_OK;
                LPWSTR name = nullptr, uri = nullptr;
                named->get_Name(&name);
                args->get_Uri(&uri);
                const bool managed = name && uri && std::wstring(name).rfind(L"neutralino-popup:", 0) == 0
                    && std::wstring(uri) == L"about:blank";
                CoTaskMemFree(name);
                CoTaskMemFree(uri);
                if (!managed) return S_OK;
                static const ATOM window_class = [] {
                    WNDCLASSW wc = {};
                    wc.lpfnWndProc = window_proc;
                    wc.hInstance = GetModuleHandleW(nullptr);
                    wc.lpszClassName = L"NeutralinoPopupWindow";
                    wc.hCursor = LoadCursor(nullptr, IDC_ARROW);
                    return RegisterClassW(&wc);
                }();
                if (!window_class) return E_FAIL;
                com_ptr<ICoreWebView2Deferral> deferral;
                if (FAILED(args->GetDeferral(&deferral))) return E_FAIL;
                args->put_Handled(TRUE);
                com_ptr<ICoreWebView2WindowFeatures> features;
                args->get_WindowFeatures(&features);
                BOOL has_size = FALSE;
                UINT width = 800, height = 600;
                features->get_HasSize(&has_size);
                if (has_size) { features->get_Width(&width); features->get_Height(&height); }
                const auto dpi = GetDpiForWindow(owner);
                RECT rect = {0, 0, MulDiv(static_cast<int>(std::clamp(width, 200u, 8192u)), dpi, 96),
                    MulDiv(static_cast<int>(std::clamp(height, 150u, 8192u)), dpi, 96)};
                AdjustWindowRectExForDpi(&rect, WS_OVERLAPPEDWINDOW, FALSE, 0, dpi);
                auto popup = std::make_shared<popup_window>();
                auto holder = new std::shared_ptr<popup_window>(popup);
                HWND window = CreateWindowExW(0, MAKEINTATOM(window_class), L"", WS_OVERLAPPEDWINDOW,
                    CW_USEDEFAULT, CW_USEDEFAULT, rect.right - rect.left, rect.bottom - rect.top,
                    owner, nullptr, GetModuleHandleW(nullptr), holder);
                if (!window) { if (!popup->attached_) delete holder; deferral->Complete(); return E_FAIL; }
                SendMessageW(window, WM_SETICON, ICON_SMALL, SendMessageW(owner, WM_GETICON, ICON_SMALL, 0));
                SendMessageW(window, WM_SETICON, ICON_BIG, SendMessageW(owner, WM_GETICON, ICON_BIG, 0));
                com_ptr<ICoreWebView2NewWindowRequestedEventArgs> request = args;
                com_ptr<ICoreWebView2> source_view = sender;
                HRESULT result = env->CreateCoreWebView2Controller(window,
                    Microsoft::WRL::Callback<ICoreWebView2CreateCoreWebView2ControllerCompletedHandler>(
                        [popup, request, source_view, deferral](HRESULT error, ICoreWebView2Controller* controller) -> HRESULT {
                            if (SUCCEEDED(error) && controller && popup->window_)
                                popup->initialize(controller, source_view.Get(), request.Get());
                            else {
                                if (controller) controller->Close();
                                if (popup->window_) DestroyWindow(popup->window_);
                            }
                            deferral->Complete();
                            return S_OK;
                        }).Get());
                if (FAILED(result)) { DestroyWindow(window); deferral->Complete(); }
                return result;
            }).Get(), &token);
    }
};
} // namespace webview
