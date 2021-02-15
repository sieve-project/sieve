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

func instrumentEnqueue() {
	instrumentEnqueueGo("vanilla/enqueue.go", "auto-instr/enqueue.go")
	instrumentEnqueueGo("vanilla/enqueue_owner.go", "auto-instr/enqueue_owner.go")
	instrumentEnqueueGo("vanilla/enqueue_mapped.go", "auto-instr/enqueue_mapped.go")
}

func instrumentEnqueueGo(ifile, ofile string) {
	fmt.Println(ifile)
	code, err := ioutil.ReadFile(ifile)
	check(err)
	dec := decorator.NewDecoratorWithImports(token.NewFileSet(), "handler", goast.New())
	f, err := dec.Parse(code)
	check(err)
	instrumentBeforeAdd(f)

	res := decorator.NewRestorerWithImports("handler", guess.New())

	autoInstrFile, err := os.Create(ofile)
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
