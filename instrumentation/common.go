package main

import (
	"bytes"
	"strings"
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
	fres.Alias["k8s.io/klog/v2"] = "klog"

	autoInstrFile, err := os.Create(ofilepath)
	check(err)
	defer autoInstrFile.Close()
	var buf bytes.Buffer
	err = fres.Fprint(&buf, f)
	autoInstrFile.Write(buf.Bytes())
	check(err)
}

func instrumentClientGoForAll(ifilepath, ofilepath, mode string) {
	funName := "Notify" + mode + "SideEffects"
	f := parseSourceFile(ifilepath, "client")
	_, funcDecl := findFuncDecl(f, "Create")
	index := 0
	if funcDecl != nil {
		instrumentation := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: funName, Path: "sonar.client"},
				Args: []dst.Expr{&dst.Ident{Name: "\"create\""}, &dst.Ident{Name: "obj"}},
			},
		}
		instrumentation.Decs.End.Append("//sonar")
		insertStmt(&funcDecl.Body.List, index, instrumentation)
	}

	_, funcDecl = findFuncDecl(f, "Update")
	if funcDecl != nil {
		instrumentation := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: funName, Path: "sonar.client"},
				Args: []dst.Expr{&dst.Ident{Name: "\"update\""}, &dst.Ident{Name: "obj"}},
			},
		}
		instrumentation.Decs.End.Append("//sonar")
		insertStmt(&funcDecl.Body.List, index, instrumentation)
	}

	_, funcDecl = findFuncDecl(f, "Delete")
	if funcDecl != nil {
		instrumentation := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: funName, Path: "sonar.client"},
				Args: []dst.Expr{&dst.Ident{Name: "\"delete\""}, &dst.Ident{Name: "obj"}},
			},
		}
		instrumentation.Decs.End.Append("//sonar")
		insertStmt(&funcDecl.Body.List, index, instrumentation)
	}

	writeInstrumentedFile(ofilepath, "client", f)
}

func preprocess(path string) {
	read, err := ioutil.ReadFile(path)
	check(err)
	newContents := strings.Replace(string(read), "\"k8s.io/klog/v2\"", "klog \"k8s.io/klog/v2\"", 1)
	err = ioutil.WriteFile(path, []byte(newContents), 0)
	check(err)
}
