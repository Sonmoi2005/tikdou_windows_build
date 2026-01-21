# Build TikTokDownloader for Windows

This folder contains a version of the TikTok/Douyin downloader that is ready to be packaged as a native Windows executable using PyInstaller. The Python sources have been adjusted to better support running as a `.exe`:

* **Cookies handling**: When running from a bundled executable, the app looks for `cookies_douyin.txt` or `cookies.txt` **in the same folder as the `.exe`** instead of relying on `__file__`.
* **FFmpeg discovery**: The downloader will first look for `ffmpeg.exe` in the same directory as the executable, then in a `ffmpeg\bin` subfolder, and finally fall back to an `ffmpeg` available in the system `PATH`.
* **User‐Agent on Douyin**: For improved compatibility, the Douyin requests now use a Windows Chrome user‑agent string.

## Building on Windows

1. Install Python 3.11 (or compatible) on your Windows machine. Ensure `python` is available in your `PATH`.
2. Open a command prompt and change into this directory.
3. Run either of the provided batch files:

   * `build_onedir_windows.bat` – builds a **folder** distribution under `dist\TikTokDownloader`. This distribution includes all the dependencies alongside the main executable and is the most robust.
   * `build_onefile_windows.bat` – builds a **single** executable `dist\TikTokDownloader.exe`. This option produces just one file but may have slightly longer startup time.

4. After the script finishes, look in the `dist` folder for your built executable. Double‑click `TikTokDownloader.exe` to start the downloader.

### Packaging with FFmpeg

If you would like the packaged application to include FFmpeg so users do not need to install it separately, copy `ffmpeg.exe` (or an `ffmpeg\bin\ffmpeg.exe` folder) into the same directory as the built executable or into the project root **before** running the build script. The bundler will detect it automatically at runtime.

---

**Note:** Building Windows executables from a non‑Windows environment is not supported by PyInstaller. To generate the `.exe` you must run the build on a Windows machine or use a CI service like GitHub Actions that provides a Windows runner. See `.github/workflows/build-windows.yml` for an example.