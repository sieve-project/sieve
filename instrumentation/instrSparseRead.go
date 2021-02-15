package main

import (
	"bytes"
	"fmt"
	"go/token"
	"io/ioutil"
	"os"

	"github.com/dave/dst"
	"github.com/dave/dst/decorator"
	"github.com/dave/dst/decorator/resolver/goast"
	"github.com/dave/dst/decorator/resolver/guess"
)

func instrumentControllerGo(ifilepath, ofilepath string) {
	code, err := ioutil.ReadFile(ifilepath)
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

	autoInstrFile, err := os.Create(ofilepath)
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

func instrumentEnqueueGo(ifilepath, ofilepath string) {
	code, err := ioutil.ReadFile(ifilepath)
	check(err)
	dec := decorator.NewDecoratorWithImports(token.NewFileSet(), "handler", goast.New())
	f, err := dec.Parse(code)
	check(err)
	instrumentBeforeAdd(f)

	res := decorator.NewRestorerWithImports("handler", guess.New())

	autoInstrFile, err := os.Create(ofilepath)
	check(err)
	defer autoInstrFile.Close()
	var buf bytes.Buffer
	err = res.Fprint(&buf, f)
	autoInstrFile.Write(buf.Bytes())
	check(err)
}

func instrumentBeforeAdd(f *dst.File) {
	for _, decl := range f.Decls {
		if funcDecl, ok := decl.(*dst.FuncDecl); ok {
			instrumentBeforeAddInList(&funcDecl.Body.List)
		}
	}
}

func instrumentBeforeAddInList(list *[]dst.Stmt) {
	var toInstrument []int
	for i, stmt := range *list {
		switch stmt.(type) {
		case *dst.ExprStmt:
			exprStmt := stmt.(*dst.ExprStmt)
			if callExpr, ok := exprStmt.X.(*dst.CallExpr); ok {
				if selectorExpr, ok := callExpr.Fun.(*dst.SelectorExpr); ok {
					if selectorExpr.Sel.Name == "Add" {
						fmt.Println("find Add")
						toInstrument = append(toInstrument, i)
					}
				}
			}
		case *dst.IfStmt:
			ifStmt := stmt.(*dst.IfStmt)
			instrumentBeforeAddInList(&ifStmt.Body.List)
		case *dst.ForStmt:
			forStmt := stmt.(*dst.ForStmt)
			instrumentBeforeAddInList(&forStmt.Body.List)
		case *dst.RangeStmt:
			rangeStmt := stmt.(*dst.RangeStmt)
			instrumentBeforeAddInList(&rangeStmt.Body.List)
		default:
		}
	}

	for _, index := range toInstrument {
		*list = append((*list)[:index+1], (*list)[index:]...)
		instrumentation := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: "PushIntoQueue", Path: "sonar.client/pkg/sonar"},
				Args: []dst.Expr{&dst.Ident{Name: "q"}},
			},
		}
		instrumentation.Decs.Start.Append("//sonar: PushIntoQueue")
		(*list)[index] = instrumentation
	}
}
