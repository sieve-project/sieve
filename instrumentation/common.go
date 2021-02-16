package main

import (
	"bytes"
	"os"

	"github.com/dave/dst"
	"github.com/dave/dst/decorator"
	"github.com/dave/dst/decorator/resolver/guess"
)

func check(e error) {
	if e != nil {
		panic(e)
	}
}

func findFuncDecl(f *dst.File, funName string) (int, *dst.FuncDecl) {
	for i, decl := range f.Decls {
		if funcDecl, ok := decl.(*dst.FuncDecl); ok {
			if funcDecl.Name.Name == funName {
				return i, funcDecl
			}
		}
	}
	return -1, nil
}

func writeInstrumentedFile(path, ofilepath string, f *dst.File) {
	res := decorator.NewRestorerWithImports(path, guess.New())

	autoInstrFile, err := os.Create(ofilepath)
	check(err)
	defer autoInstrFile.Close()
	var buf bytes.Buffer
	err = res.Fprint(&buf, f)
	autoInstrFile.Write(buf.Bytes())
	check(err)
}
