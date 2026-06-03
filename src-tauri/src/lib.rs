use std::sync::Mutex;

pub const BACKEND_PORT: u16 = 8765;

// Process handle lives for the whole app lifetime — static mutex is the
// correct pattern here because on_window_event closures can't borrow
// Tauri `State<'_>` across the destructor boundary.
static BACKEND: Mutex<Option<std::process::Child>> = Mutex::new(None);

fn wait_for_backend(port: u16, attempts: u32) {
    for _ in 0..attempts {
        if std::net::TcpStream::connect(format!("127.0.0.1:{port}")).is_ok() {
            return;
        }
        std::thread::sleep(std::time::Duration::from_millis(300));
    }
}

fn spawn_backend(backend_dir: &std::path::Path) -> std::io::Result<std::process::Child> {
    let python = {
        // Windows venv: Scripts\python.exe  |  Unix venv: bin/python3
        let venv_python = if cfg!(target_os = "windows") {
            backend_dir.join("venv\\Scripts\\python.exe")
        } else {
            backend_dir.join("venv/bin/python3")
        };
        if venv_python.exists() {
            venv_python.to_string_lossy().into_owned()
        } else if cfg!(target_os = "windows") {
            "python".to_string()   // Windows doesn't always have `python3` in PATH
        } else {
            "python3".to_string()
        }
    };

    std::process::Command::new(python)
        .args([
            "-m",
            "uvicorn",
            "server:app",
            "--host",
            "127.0.0.1",
            "--port",
            &BACKEND_PORT.to_string(),
            "--log-level",
            "warning",
        ])
        .current_dir(backend_dir)
        .spawn()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // CARGO_MANIFEST_DIR is src-tauri/; backend/ lives one level up.
            let backend_dir = if cfg!(debug_assertions) {
                std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                    .parent()
                    .unwrap()
                    .join("backend")
            } else {
                use tauri::Manager;
                app.path()
                    .resource_dir()
                    .unwrap_or_default()
                    .join("backend")
            };

            match spawn_backend(&backend_dir) {
                Ok(child) => {
                    *BACKEND.lock().unwrap() = Some(child);
                    wait_for_backend(BACKEND_PORT, 50);
                }
                Err(e) => {
                    eprintln!("Failed to start Python backend: {e}");
                }
            }

            Ok(())
        })
        .on_window_event(|_window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if let Ok(mut guard) = BACKEND.lock() {
                    if let Some(mut child) = guard.take() {
                        let _ = child.kill();
                    }
                }
            }
        })
        .invoke_handler(tauri::generate_handler![get_backend_port])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[tauri::command]
fn get_backend_port() -> u16 {
    BACKEND_PORT
}
