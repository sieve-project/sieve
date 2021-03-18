package main

import (
	"bytes"
	"go/token"
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

func findTypeDecl(f *dst.File, typeName string) (int, int, *dst.TypeSpec) {
	for i, decl := range f.Decls {
		if genDecl, ok := decl.(*dst.GenDecl); ok && genDecl.Tok == token.TYPE {
			for j, spec := range genDecl.Specs {
				if typeSpec, ok := spec.(*dst.TypeSpec); ok {
					if typeSpec.Name.Name == typeName {
						return i, j, typeSpec
					}
				}
			}
		}
	}
	return -1, -1, nil
}

func writeInstrumentedFile(path, ofilepath string, f *dst.File) {
	res := decorator.NewRestorerWithImports(path, guess.New())
	fres := res.FileRestorer()
	fres.Alias["sonar.client"] = "sonar"

	autoInstrFile, err := os.Create(ofilepath)
	check(err)
	defer autoInstrFile.Close()
	var buf bytes.Buffer
	err = fres.Fprint(&buf, f)
	autoInstrFile.Write(buf.Bytes())
	check(err)
}
