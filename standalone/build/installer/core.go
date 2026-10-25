package main

import (
	"archive/zip"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

var releaseVersion = "0.6.0"

func extract(payload []byte, root, version string) (string, error) {
	if !regexp.MustCompile(`^\d+\.\d+\.\d+$`).MatchString(version) {
		return "", fmt.Errorf("invalid version")
	}
	versions := filepath.Join(root, "versions")
	if err := os.MkdirAll(versions, 0700); err != nil {
		return "", err
	}
	stage, err := os.MkdirTemp(versions, ".install-")
	if err != nil {
		return "", err
	}
	defer os.RemoveAll(stage)
	reader, err := zip.NewReader(bytes.NewReader(payload), int64(len(payload)))
	if err != nil {
		return "", err
	}
	seen := map[string]bool{}
	var total uint64
	for _, entry := range reader.File {
		name := strings.TrimPrefix(entry.Name, "Shiur Player/")
		if name == entry.Name || name == "" || strings.ContainsAny(name, `\:`) || strings.HasPrefix(name, "/") {
			return "", fmt.Errorf("invalid archive path: %s", entry.Name)
		}
		for _, part := range strings.Split(name, "/") {
			if part == ".." || part == "." {
				return "", fmt.Errorf("invalid archive path")
			}
		}
		if entry.Mode()&os.ModeSymlink != 0 {
			return "", fmt.Errorf("archive symlink is not allowed")
		}
		key := strings.ToLower(name)
		if seen[key] {
			return "", fmt.Errorf("duplicate archive path")
		}
		seen[key] = true
		if entry.UncompressedSize64 > 512*1024*1024-total {
			return "", fmt.Errorf("archive exceeds installation size limit")
		}
		total += entry.UncompressedSize64
		destination := filepath.Join(stage, filepath.FromSlash(name))
		if entry.FileInfo().IsDir() {
			if err = os.MkdirAll(destination, 0700); err != nil {
				return "", err
			}
			continue
		}
		if err = os.MkdirAll(filepath.Dir(destination), 0700); err != nil {
			return "", err
		}
		input, e := entry.Open()
		if e != nil {
			return "", e
		}
		output, e := os.OpenFile(destination, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
		if e != nil {
			input.Close()
			return "", e
		}
		_, e = io.Copy(output, io.LimitReader(input, int64(entry.UncompressedSize64)+1))
		closeErr := output.Close()
		input.Close()
		if e != nil {
			return "", e
		}
		if closeErr != nil {
			return "", closeErr
		}
	}
	for _, name := range []string{"Shiur Player.exe", "main.py", "runtime/python/pythonw.exe", "runtime/vlc/libvlc.dll"} {
		if _, err = os.Stat(filepath.Join(stage, filepath.FromSlash(name))); err != nil {
			return "", fmt.Errorf("incomplete installer: %s", name)
		}
	}
	target := filepath.Join(versions, version)
	if _, err = os.Stat(target); err == nil {
		// A same-version reinstall must repair damaged files, not silently reuse them.
		backup, backupErr := os.MkdirTemp(versions, ".repair-"+version+"-")
		if backupErr != nil {
			return "", backupErr
		}
		if err = os.Remove(backup); err != nil {
			return "", err
		}
		if err = os.Rename(target, backup); err != nil {
			return "", err
		}
		if err = os.Rename(stage, target); err != nil {
			if restoreErr := os.Rename(backup, target); restoreErr != nil {
				return "", fmt.Errorf("repair failed (%v); original files retained at %s: %w", err, backup, restoreErr)
			}
			return "", err
		}
		// A cleanup failure may leave a spare program copy, never delete the active copy.
		_ = os.RemoveAll(backup)
		return target, nil
	} else if !os.IsNotExist(err) {
		return "", err
	}
	if err = os.Rename(stage, target); err != nil {
		return "", err
	}
	return target, nil
}
func activate(root, version string) error {
	if !regexp.MustCompile(`^\d+\.\d+\.\d+$`).MatchString(version) {
		return fmt.Errorf("invalid version")
	}
	if _, err := os.Stat(filepath.Join(root, "versions", version, "Shiur Player.exe")); err != nil {
		return err
	}
	data, _ := json.Marshal(map[string]string{"version": version})
	temp, err := os.CreateTemp(root, ".active-")
	if err != nil {
		return err
	}
	name := temp.Name()
	defer os.Remove(name)
	if _, err = temp.Write(data); err != nil {
		temp.Close()
		return err
	}
	if err = temp.Sync(); err != nil {
		temp.Close()
		return err
	}
	if err = temp.Close(); err != nil {
		return err
	}
	return os.Rename(name, filepath.Join(root, "active.json"))
}
