package main

import (
	"bytes"
	"go/token"
	"os"
	"io/ioutil"
	"github.com/dave/dst/decorator/resolver/goast"

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

func parseSourceFile(ifilepath, pkg string) *dst.File {
	code, err := ioutil.ReadFile(ifilepath)
	check(err)
	dec := decorator.NewDecoratorWithImports(token.NewFileSet(), pkg, goast.New())
	f, err := dec.Parse(code)
	check(err)
	return f
}

func insertStmt(list *[]dst.Stmt, index int, instrumentation dst.Stmt) {
	*list = append((*list)[:index+1], (*list)[index:]...)
	(*list)[index] = instrumentation
}

func insertDecl(list *[]dst.Decl, index int, instrumentation dst.Decl) {
	*list = append((*list)[:index+1], (*list)[index:]...)
	(*list)[index] = instrumentation
}

func writeInstrumentedFile(ofilepath, pkg string, f *dst.File) {
	res := decorator.NewRestorerWithImports(pkg, guess.New())
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
