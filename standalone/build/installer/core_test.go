package main

import (
	"archive/zip"
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func archive(entries map[string]string) []byte {
	var buf bytes.Buffer
	z := zip.NewWriter(&buf)
	for name, data := range entries {
		w, _ := z.Create(name)
		w.Write([]byte(data))
	}
	z.Close()
	return buf.Bytes()
}
func valid() map[string]string {
	return map[string]string{"Shiur Player/Shiur Player.exe": "exe", "Shiur Player/main.py": "main", "Shiur Player/runtime/python/pythonw.exe": "python", "Shiur Player/runtime/vlc/libvlc.dll": "vlc"}
}
func TestInstallAndUpdateKeepUserData(t *testing.T) {
	home := t.TempDir()
	root := filepath.Join(home, "Programs", "ShiurPlayer")
	data := filepath.Join(home, "ShiurPlayerStandalone")
	os.MkdirAll(data, 0700)
	state := filepath.Join(data, "state.json")
	os.WriteFile(state, []byte(`{"position":65.432}`), 0600)
	if _, e := extract(archive(valid()), root, "0.6.0"); e != nil {
		t.Fatal(e)
	}
	if e := activate(root, "0.6.0"); e != nil {
		t.Fatal(e)
	}
	if _, e := extract(archive(valid()), root, "0.6.1"); e != nil {
		t.Fatal(e)
	}
	if e := activate(root, "0.6.1"); e != nil {
		t.Fatal(e)
	}
	raw, _ := os.ReadFile(filepath.Join(root, "active.json"))
	var active map[string]string
	json.Unmarshal(raw, &active)
	if active["version"] != "0.6.1" {
		t.Fatal(active)
	}
	saved, _ := os.ReadFile(state)
	if string(saved) != `{"position":65.432}` {
		t.Fatal("saved listening positions changed")
	}
	if _, e := os.Stat(filepath.Join(root, "versions", "0.6.0", "main.py")); e != nil {
		t.Fatal("previous version was lost")
	}
}
func TestBadArchiveLeavesPreviousVersionActive(t *testing.T) {
	root := t.TempDir()
	extract(archive(valid()), root, "0.6.0")
	activate(root, "0.6.0")
	before, _ := os.ReadFile(filepath.Join(root, "active.json"))
	for _, name := range []string{"Shiur Player/../escape.exe", "Shiur Player/C:/escape.exe", "Shiur Player/dir\\escape.exe", "outside/main.py"} {
		entries := valid()
		entries[name] = "bad"
		if _, e := extract(archive(entries), root, "0.6.1"); e == nil {
			t.Fatalf("accepted %s", name)
		}
	}
	if _, e := extract(archive(map[string]string{"Shiur Player/main.py": "incomplete"}), root, "0.6.1"); e == nil {
		t.Fatal("incomplete payload accepted")
	}
	if e := activate(root, "0.6.1"); e == nil {
		t.Fatal("missing version activated")
	}
	after, _ := os.ReadFile(filepath.Join(root, "active.json"))
	if !bytes.Equal(before, after) {
		t.Fatal("previous active version changed")
	}
}

func TestActualBundledPayload(t *testing.T) {
	file := os.Getenv("SHIUR_INSTALL_PAYLOAD")
	if file == "" {
		t.Skip("No release payload specified")
	}
	payload, err := os.ReadFile(file)
	if err != nil {
		t.Fatal(err)
	}
	root := t.TempDir()
	target, err := extract(payload, root, "0.6.0")
	if err != nil {
		t.Fatal(err)
	}
	for _, name := range []string{"updater.py", "version.py", "runtime/python/_tkinter.pyd", "runtime/tcl/tk8.6/tk.tcl"} {
		if _, err = os.Stat(filepath.Join(target, filepath.FromSlash(name))); err != nil {
			t.Fatal(err)
		}
	}
	if err = activate(root, "0.6.0"); err != nil {
		t.Fatal(err)
	}
}

func TestReinstallRepairsExistingVersionWithoutChangingProfile(t *testing.T) {
	root := t.TempDir()
	original := archive(valid())
	target, err := extract(original, root, "0.9.4")
	if err != nil {
		t.Fatal(err)
	}
	if err := activate(root, "0.9.4"); err != nil {
		t.Fatal(err)
	}
	before, _ := os.ReadFile(filepath.Join(root, "active.json"))
	if err := os.WriteFile(filepath.Join(target, "main.py"), []byte("broken"), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := extract(original, root, "0.9.4"); err != nil {
		t.Fatal(err)
	}
	data, _ := os.ReadFile(filepath.Join(target, "main.py"))
	if string(data) != "main" {
		t.Fatal("reinstallation left corrupted program files in place")
	}
	after, _ := os.ReadFile(filepath.Join(root, "active.json"))
	if !bytes.Equal(before, after) {
		t.Fatal("repair changed the selected release")
	}
	if _, err := extract(archive(map[string]string{"Shiur Player/main.py": "invalid"}), root, "0.9.4"); err == nil {
		t.Fatal("invalid repair payload accepted")
	}
	data, _ = os.ReadFile(filepath.Join(target, "main.py"))
	if string(data) != "main" {
		t.Fatal("failed repair damaged existing files")
	}
}
