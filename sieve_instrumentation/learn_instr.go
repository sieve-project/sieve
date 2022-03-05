package main

import (
	"fmt"

	"github.com/dave/dst"
)

func instrumentControllerGoForLearn(ifilepath, ofilepath string) {
	f := parseSourceFile(ifilepath, "controller", map[string]string{})
	_, funcDecl := findFuncDecl(f, "reconcileHandler", "*Controller")
	if funcDecl != nil {
		index := 0
		beforeReconcileInstrumentation := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: "NotifyLearnBeforeReconcile", Path: "sieve.client"},
				Args: []dst.Expr{&dst.Ident{Name: "c.Do"}},
			},
		}
		beforeReconcileInstrumentation.Decs.End.Append("//sieve")
		insertStmt(&funcDecl.Body.List, index, beforeReconcileInstrumentation)

		index += 1
		afterReconcileInstrumentation := &dst.DeferStmt{
			Call: &dst.CallExpr{
				Fun:  &dst.Ident{Name: "NotifyLearnAfterReconcile", Path: "sieve.client"},
				Args: []dst.Expr{&dst.Ident{Name: "c.Do"}},
			},
		}
		afterReconcileInstrumentation.Decs.End.Append("//sieve")
		insertStmt(&funcDecl.Body.List, index, afterReconcileInstrumentation)
	} else {
		panic(fmt.Errorf("Cannot find function reconcileHandler"))
	}

	writeInstrumentedFile(ofilepath, "controller", f, map[string]string{})
}
