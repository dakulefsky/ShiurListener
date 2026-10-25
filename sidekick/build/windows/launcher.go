// Windows console launcher for the bundled, local Python runtime.
package main

import (
 "bufio"
 "fmt"
 "os"
 "os/exec"
 "path/filepath"
)

func fail(err error) {
 fmt.Fprintln(os.Stderr, "\nCould not start Sidekick:", err)
 fmt.Fprintln(os.Stderr, "Extract the entire ZIP first, then run Sidekick.exe from the extracted folder.\nPress Enter to close.")
 _, _ = bufio.NewReader(os.Stdin).ReadString('\n')
 os.Exit(1)
}
func main() {
 executable, err := os.Executable()
 if err != nil { fail(err) }
 directory := filepath.Dir(executable)
 python := filepath.Join(directory,"runtime","python","python.exe")
 script := filepath.Join(directory,"companion.py")
 for _, file := range []string{python,script,filepath.Join(directory,"runtime","vlc","libvlc.dll")} {
  if _, err := os.Stat(file); err != nil { fail(err) }
 }
 fmt.Println("Sidekick — portable shiur player")
 fmt.Println("Python and VLC are bundled. Keep this window open while listening.")
 arguments := append([]string{"-I","-u",script},os.Args[1:]...)
 command := exec.Command(python,arguments...)
 command.Dir = directory
 command.Stdin = os.Stdin
 command.Stdout = os.Stdout
 command.Stderr = os.Stderr
 if err := command.Run(); err != nil { fail(err) }
}
