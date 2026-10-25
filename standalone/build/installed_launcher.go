// Stable per-user entrypoint. Updates change active.json, not this running file.
package main

import (
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"syscall"
	"unsafe"
)

func main() {
	file, err := os.Executable()
	if err != nil {
		return
	}
	root := filepath.Dir(file)
	var active struct {
		Version string `json:"version"`
	}
	data, err := os.ReadFile(filepath.Join(root, "active.json"))
	if err == nil {
		err = json.Unmarshal(data, &active)
	}
	if err != nil || !regexp.MustCompile(`^\d+\.\d+\.\d+$`).MatchString(active.Version) {
		message("Shiur Player needs to be installed again.")
		return
	}
	executable := filepath.Join(root, "versions", active.Version, "Shiur Player.exe")
	command := exec.Command(executable, os.Args[1:]...)
	command.Dir = filepath.Dir(executable)
	command.SysProcAttr = &syscall.SysProcAttr{HideWindow: true, CreationFlags: 0x08000000}
	if err := command.Run(); err != nil {
		message("Shiur Player could not start. Run its setup file again.\n" + err.Error())
	}
}
func message(value string) {
	text, _ := syscall.UTF16PtrFromString(value)
	title, _ := syscall.UTF16PtrFromString("Shiur Player")
	syscall.NewLazyDLL("user32.dll").NewProc("MessageBoxW").Call(0, uintptr(unsafe.Pointer(text)), uintptr(unsafe.Pointer(title)), 0x10)
}
