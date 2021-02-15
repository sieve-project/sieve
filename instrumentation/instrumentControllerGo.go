package main

import (
	"bytes"
	"go/token"
	"io/ioutil"
	"os"

	"github.com/dave/dst"
	"github.com/dave/dst/decorator"
	"github.com/dave/dst/decorator/resolver/goast"
	"github.com/dave/dst/decorator/resolver/guess"
)

func instrumentControllerGo() {
	code, err := ioutil.ReadFile("vanilla/controller.go")
	check(err)
	dec := decorator.NewDecoratorWithImports(token.NewFileSet(), "controller", goast.New())
	f, err := dec.Parse(code)
	check(err)

	funcDecl := findFuncDecl(f, "reconcileHandler")
	if funcDecl != nil {
		index, targetStmt := findCallingReconcileIfStmt(funcDecl)
		if targetStmt != nil {
			// fmt.Println(targetStmt)
			funcDecl.Body.List = append(funcDecl.Body.List[:index+1], funcDecl.Body.List[index:]...)
			instrumentation := &dst.ExprStmt{
				X: &dst.CallExpr{
					Fun:  &dst.Ident{Name: "WaitBeforeReconcile", Path: "sonar.client/pkg/sonar"},
					Args: []dst.Expr{&dst.Ident{Name: "c.Name"}},
				},
			}
			instrumentation.Decs.Start.Append("//sonar: WaitBeforeReconcile")
			funcDecl.Body.List[index] = instrumentation
		}
	}

	funcDecl = findFuncDecl(f, "Start")
	if funcDecl != nil {
		index, targetStmt := findCallingMakeQueue(funcDecl)
		if targetStmt != nil {
			index = index + 1
			funcDecl.Body.List = append(funcDecl.Body.List[:index+1], funcDecl.Body.List[index:]...)
			instrumentation := &dst.ExprStmt{
				X: &dst.CallExpr{
					Fun:  &dst.Ident{Name: "RegisterQueue", Path: "sonar.client/pkg/sonar"},
					Args: []dst.Expr{&dst.Ident{Name: "c.Queue"}, &dst.Ident{Name: "c.Name"}},
				},
			}
			instrumentation.Decs.Start.Append("//sonar: RegisterQueue")
			funcDecl.Body.List[index] = instrumentation
		}
	}

	res := decorator.NewRestorerWithImports("controller", guess.New())

	autoInstrFile, err := os.Create("auto-instr/controller.go")
	check(err)
	defer autoInstrFile.Close()
	var buf bytes.Buffer
	err = res.Fprint(&buf, f)
	autoInstrFile.Write(buf.Bytes())
	check(err)
}

func findCallingReconcileIfStmt(funcDecl *dst.FuncDecl) (int, *dst.IfStmt) {
	for i, stmt := range funcDecl.Body.List {
		if ifStmt, ok := stmt.(*dst.IfStmt); ok {
			if assignStmt, ok := ifStmt.Init.(*dst.AssignStmt); ok {
				if callExpr, ok := assignStmt.Rhs[0].(*dst.CallExpr); ok {
					if selectorExpr, ok := callExpr.Fun.(*dst.SelectorExpr); ok {
						if selectorExpr.Sel.Name == "Reconcile" {
							return i, ifStmt
						}
					}
				}
			}
		}
	}
	return -1, nil
}

func findCallingMakeQueue(funcDecl *dst.FuncDecl) (int, *dst.AssignStmt) {
	for i, stmt := range funcDecl.Body.List {
		if assignStmt, ok := stmt.(*dst.AssignStmt); ok {
			if callExpr, ok := assignStmt.Rhs[0].(*dst.CallExpr); ok {
				if selectorExpr, ok := callExpr.Fun.(*dst.SelectorExpr); ok {
					if selectorExpr.Sel.Name == "MakeQueue" {
						return i, assignStmt
					}
				}
			}
		}
	}
	return -1, nil
}
