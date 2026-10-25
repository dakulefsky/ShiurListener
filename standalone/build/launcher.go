// GUI launcher for the standalone player; reopening shows its existing window.
package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"syscall"
	"unsafe"
)

var user = syscall.NewLazyDLL("user32.dll")

func ptr(value string) *uint16 { p, _ := syscall.UTF16PtrFromString(value); return p }
func fail(message string) {
	text, title := ptr(message), ptr("Shiur Player")
	user.NewProc("MessageBoxW").Call(0, uintptr(unsafe.Pointer(text)), uintptr(unsafe.Pointer(title)), 0x10)
	runtime.KeepAlive(text)
	runtime.KeepAlive(title)
	os.Exit(1)
}
func main() {
	className := ptr("ShiurPlayerStandaloneWindow")
	existing, _, _ := user.NewProc("FindWindowW").Call(uintptr(unsafe.Pointer(className)), 0)
	runtime.KeepAlive(className)
	if existing != 0 {
		user.NewProc("PostMessageW").Call(existing, 0x800B, 0, 0)
		return
	}
	executable, err := os.Executable()
	if err != nil {
		fail(err.Error())
	}
	directory := filepath.Dir(executable)
	python := filepath.Join(directory, "runtime", "python", "pythonw.exe")
	script := filepath.Join(directory, "main.py")
	for _, file := range []string{python, script, filepath.Join(directory, "window.py"), filepath.Join(directory, "engine.py"), filepath.Join(directory, "controller.py"), filepath.Join(directory, "folder_picker.py"), filepath.Join(directory, "floating_bar.py"), filepath.Join(directory, "hotkeys.py"), filepath.Join(directory, "runtime", "vlc", "libvlc.dll")} {
		if _, err := os.Stat(file); err != nil {
			fail("Extract the entire ZIP first. Missing file: " + file)
		}
	}
	args := append([]string{"-I", "-u", script}, os.Args[1:]...)
	command := exec.Command(python, args...)
	command.Dir = directory
	command.SysProcAttr = &syscall.SysProcAttr{HideWindow: true, CreationFlags: 0x08000000}
	if err := command.Run(); err != nil {
		fail("The player could not start. Keep the complete extracted folder together.\n" + err.Error())
	}
}
