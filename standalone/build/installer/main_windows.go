package main

import (
	"bytes"
	_ "embed"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"syscall"
	"unsafe"
)

//go:embed payload.zip
var payload []byte

//go:embed installed-launcher.exe
var launcher []byte
var user = syscall.NewLazyDLL("user32.dll")
var kernel = syscall.NewLazyDLL("kernel32.dll")

func wide(s string) *uint16 { p, _ := syscall.UTF16PtrFromString(s); return p }
func notice(s string, flags uintptr) uintptr {
	p, t := wide(s), wide("Shiur Player Setup")
	result, _, _ := user.NewProc("MessageBoxW").Call(0, uintptr(unsafe.Pointer(p)), uintptr(unsafe.Pointer(t)), flags)
	runtime.KeepAlive(p)
	runtime.KeepAlive(t)
	return result
}
func main() {
	if err := setup(); err != nil {
		notice(err.Error(), 0x10)
		os.Exit(1)
	}
}
func setup() error {
	update := len(os.Args) == 3 && os.Args[1] == "--update"
	mutexName := wide("Local\\ShiurPlayerSetup")
	mutex, _, err := kernel.NewProc("CreateMutexW").Call(0, 0, uintptr(unsafe.Pointer(mutexName)))
	runtime.KeepAlive(mutexName)
	if mutex == 0 {
		return err
	}
	defer kernel.NewProc("CloseHandle").Call(mutex)
	if err == syscall.Errno(183) {
		return fmt.Errorf("Another Shiur Player setup is running.")
	}
	if update {
		pid, e := strconv.Atoi(os.Args[2])
		if e != nil || pid <= 0 {
			return fmt.Errorf("Invalid update process.")
		}
		process, _, _ := kernel.NewProc("OpenProcess").Call(0x00100000, 0, uintptr(pid))
		if process != 0 {
			result, _, _ := kernel.NewProc("WaitForSingleObject").Call(process, 60000)
			kernel.NewProc("CloseHandle").Call(process)
			if result != 0 {
				return fmt.Errorf("The player is still open. Close it and run this setup file again.")
			}
		}
	} else if notice("Install Shiur Player for your Windows account?\n\nYour recordings and saved positions will be kept. No administrator access or separate runtime installation is needed.", 0x21) != 1 {
		return nil
	}
	title := wide("Shiur Player — Your listening library")
	existing, _, _ := user.NewProc("FindWindowW").Call(0, uintptr(unsafe.Pointer(title)))
	runtime.KeepAlive(title)
	if existing != 0 {
		return fmt.Errorf("Close the currently running Shiur Player, then run this setup file again. Your listening positions will be kept.")
	}
	local := os.Getenv("LOCALAPPDATA")
	if local == "" {
		return fmt.Errorf("Windows LOCALAPPDATA folder is unavailable.")
	}
	root := filepath.Join(local, "Programs", "ShiurPlayer")
	if _, err := extract(payload, root, releaseVersion); err != nil {
		return fmt.Errorf("Could not install the player: %w", err)
	}
	stable := filepath.Join(root, "Shiur Player.exe")
	if current, err := os.ReadFile(stable); os.IsNotExist(err) {
		if err = os.WriteFile(stable, launcher, 0600); err != nil {
			return err
		}
	} else if err != nil {
		return err
	} else if !bytes.Equal(current, launcher) {
		// Keep the stable entrypoint from an earlier installed version. Its protocol is fixed.
	}
	if err := shortcuts(stable, root); err != nil {
		return fmt.Errorf("Could not create shortcuts: %w", err)
	}
	if err := activate(root, releaseVersion); err != nil {
		return fmt.Errorf("Could not finish installation; the previous version remains selected: %w", err)
	}
	if !update {
		notice("Shiur Player is installed.\n\nUse the Shiur Player desktop or Start menu shortcut. For future versions, choose Check for updates inside the app.", 0x40)
	}
	command := exec.Command(stable)
	command.Dir = root
	command.SysProcAttr = &syscall.SysProcAttr{HideWindow: true, CreationFlags: 0x08000000}
	return command.Start()
}

type guid struct {
	A    uint32
	B, C uint16
	D    [8]byte
}

//go:uintptrescapes
func comMethod(object uintptr, index uintptr, args ...uintptr) uintptr {
	table := *(*uintptr)(unsafe.Pointer(object))
	fn := *(*uintptr)(unsafe.Pointer(table + index*unsafe.Sizeof(uintptr(0))))
	result, _, _ := syscall.SyscallN(fn, append([]uintptr{object}, args...)...)
	return result
}
func failed(result uintptr) bool { return int32(result) < 0 }
func shortcuts(target, working string) error {
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()
	ole := syscall.NewLazyDLL("ole32.dll")
	hr, _, _ := ole.NewProc("CoInitializeEx").Call(0, 2)
	if failed(hr) {
		return fmt.Errorf("Windows shortcut service could not start (0x%x)", hr)
	}
	defer ole.NewProc("CoUninitialize").Call()
	desktop := guid{0xB4BFCC3A, 0xDB2C, 0x424C, [8]byte{0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41}}
	programs := guid{0xA77F5D77, 0x2E2B, 0x44C3, [8]byte{0xA6, 0xA2, 0xAB, 0xA6, 0x01, 0x05, 0x4A, 0x51}}
	for _, folder := range []guid{desktop, programs} {
		var pointer uintptr
		hr, _, _ := syscall.NewLazyDLL("shell32.dll").NewProc("SHGetKnownFolderPath").Call(uintptr(unsafe.Pointer(&folder)), 0, 0, uintptr(unsafe.Pointer(&pointer)))
		if failed(hr) {
			return fmt.Errorf("Windows shortcut folder is unavailable")
		}
		chars := []uint16{}
		for i := uintptr(0); i < 32768; i++ {
			c := *(*uint16)(unsafe.Pointer(pointer + i*2))
			if c == 0 {
				break
			}
			chars = append(chars, c)
		}
		directory := syscall.UTF16ToString(chars)
		ole.NewProc("CoTaskMemFree").Call(pointer)
		if err := os.MkdirAll(directory, 0700); err != nil {
			return err
		}
		if err := makeLink(filepath.Join(directory, "Shiur Player.lnk"), target, working, ole); err != nil {
			return err
		}
	}
	return nil
}
func makeLink(file, target, working string, ole *syscall.LazyDLL) error {
	cls := guid{0x00021401, 0, 0, [8]byte{0xC0, 0, 0, 0, 0, 0, 0, 0x46}}
	iid := guid{0x000214F9, 0, 0, [8]byte{0xC0, 0, 0, 0, 0, 0, 0, 0x46}}
	var link uintptr
	hr, _, _ := ole.NewProc("CoCreateInstance").Call(uintptr(unsafe.Pointer(&cls)), 0, 1, uintptr(unsafe.Pointer(&iid)), uintptr(unsafe.Pointer(&link)))
	if failed(hr) {
		return fmt.Errorf("Could not create Windows shortcut")
	}
	defer comMethod(link, 2)
	for _, item := range []struct {
		index uintptr
		text  string
	}{{20, target}, {9, working}, {7, "Shiur Player"}} {
		value := wide(item.text)
		result := comMethod(link, item.index, uintptr(unsafe.Pointer(value)))
		runtime.KeepAlive(value)
		if failed(result) {
			return fmt.Errorf("Could not configure Windows shortcut")
		}
	}
	icon := wide(filepath.Join(working, "versions", releaseVersion, "assets", "shiur-player.ico"))
	iconResult := comMethod(link, 17, uintptr(unsafe.Pointer(icon)), 0)
	runtime.KeepAlive(icon)
	if failed(iconResult) {
		return fmt.Errorf("Could not set the player shortcut icon")
	}
	persistIID := guid{0x0000010B, 0, 0, [8]byte{0xC0, 0, 0, 0, 0, 0, 0, 0x46}}
	var persist uintptr
	if failed(comMethod(link, 0, uintptr(unsafe.Pointer(&persistIID)), uintptr(unsafe.Pointer(&persist)))) {
		return fmt.Errorf("Could not save Windows shortcut")
	}
	defer comMethod(persist, 2)
	name := wide(file)
	result := comMethod(persist, 6, uintptr(unsafe.Pointer(name)), 1)
	runtime.KeepAlive(name)
	if failed(result) {
		return fmt.Errorf("Could not save Windows shortcut")
	}
	return nil
}
