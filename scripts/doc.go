// Package main generates Nix module options from Crush schema.
//
//go:generate sh -c "cd .. && go run scripts/generate-options.go -output modules/crush/options.nix"
package main
