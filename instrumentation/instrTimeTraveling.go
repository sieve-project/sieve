package main

import (
	"go/token"
	"io/ioutil"

	"github.com/dave/dst"

	"github.com/dave/dst/decorator"
	"github.com/dave/dst/decorator/resolver/goast"
)

func instrumentReflectorGo(ifilepath, ofilepath string) {
	code, err := ioutil.ReadFile(ifilepath)
	check(err)
	dec := decorator.NewDecoratorWithImports(token.NewFileSet(), "cache", goast.New())
	f, err := dec.Parse(code)
	check(err)

	_, funcDecl := findFuncDecl(f, "LastSyncResourceVersion")
	if funcDecl == nil {
		panic("instrumentReflectorGo error")
	}
	index, _ := findFuncDecl(f, "setExpectedType")
	if index == -1 {
		panic("instrumentReflectorGo error")
	}

	instrumentation := dst.Clone(funcDecl).(*dst.FuncDecl)
	instrumentation.Name = &dst.Ident{Name: "GetExpectedTypeName"}
	instrumentation.Body.List = []dst.Stmt{&dst.ReturnStmt{Results: []dst.Expr{
		&dst.Ident{Name: "r.expectedTypeName"},
	}}}
	instrumentation.Decs.Start.Replace("//soanr")
	index = index + 1
	f.Decls = append(f.Decls[:index+1], f.Decls[index:]...)
	f.Decls[index] = instrumentation

	writeInstrumentedFile("cache", ofilepath, f)
}

func instrumentCacherGo(ifilepath, ofilepath string) {
	code, err := ioutil.ReadFile(ifilepath)
	check(err)
	dec := decorator.NewDecoratorWithImports(token.NewFileSet(), "cacher", goast.New())
	f, err := dec.Parse(code)
	check(err)

	_, funcDecl := findFuncDecl(f, "NewCacherFromConfig")
	if funcDecl == nil {
		panic("instrumentCacherGo error")
	}

	index := -1
	for i, stmt := range funcDecl.Body.List {
		if assignStmt, ok := stmt.(*dst.AssignStmt); ok {
			if ident, ok := assignStmt.Lhs[0].(*dst.Ident); ok {
				if ident.Name == "reflector" {
					index = i
				}
			}
		}
	}
	if index == -1 {
		panic("instrumentCacherGo error")
	}
	instrumentation := &dst.ExprStmt{
		X: &dst.CallExpr{
			Fun: &dst.SelectorExpr{
				X:   &dst.Ident{Name: "watchCache"},
				Sel: &dst.Ident{Name: "SetExpectedTypeName"},
			},
			Args: []dst.Expr{
				&dst.CallExpr{
					Fun: &dst.SelectorExpr{
						X:   &dst.Ident{Name: "reflector"},
						Sel: &dst.Ident{Name: "GetExpectedTypeName"},
					},
					Args: []dst.Expr{},
				},
			},
		},
	}
	instrumentation.Decs.Start.Append("//sonar")
	index = index + 1
	funcDecl.Body.List = append(funcDecl.Body.List[:index+1], funcDecl.Body.List[index:]...)
	funcDecl.Body.List[index] = instrumentation

	writeInstrumentedFile("cacher", ofilepath, f)
}
