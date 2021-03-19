package main

import (
	"github.com/dave/dst"
)

func instrumentSharedInformerGoForLearn(ifilepath, ofilepath string) {
	f := parseSourceFile(ifilepath, "cache")
	_, funcDecl := findFuncDecl(f, "HandleDeltas")
	if funcDecl != nil {
		for _, stmt := range funcDecl.Body.List {
			if rangeStmt, ok := stmt.(*dst.RangeStmt); ok {
				index := 0
				instrumentation := &dst.ExprStmt{
					X: &dst.CallExpr{
						Fun:  &dst.Ident{Name: "NotifyLearnBeforeIndexerWrite", Path: "sonar.client"},
						Args: []dst.Expr{&dst.Ident{Name: "string(d.Type)"}, &dst.Ident{Name: "d.Object"}},
					},
				}
				instrumentation.Decs.End.Append("//sonar")
				insertStmt(&rangeStmt.Body.List, index, instrumentation)
				break
			}
		}
	}

	writeInstrumentedFile(ofilepath, "cache", f)
}

func instrumentControllerGoForLearn(ifilepath, ofilepath string) {
	f := parseSourceFile(ifilepath, "controller")
	_, funcDecl := findFuncDecl(f, "reconcileHandler")
	if funcDecl != nil {
		index := 0
		beforeReconcileInstrumentation := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: "NotifyLearnBeforeReconcile", Path: "sonar.client"},
				Args: []dst.Expr{},
			},
		}
		beforeReconcileInstrumentation.Decs.End.Append("//sonar")
		insertStmt(&funcDecl.Body.List, index, beforeReconcileInstrumentation)

		index += 1
		afterReconcileInstrumentation := &dst.DeferStmt{
			Call: &dst.CallExpr{
				Fun:  &dst.Ident{Name: "NotifyLearnAfterReconcile", Path: "sonar.client"},
				Args: []dst.Expr{},
			},
		}
		afterReconcileInstrumentation.Decs.End.Append("//sonar")
		insertStmt(&funcDecl.Body.List, index, afterReconcileInstrumentation)
	}

	writeInstrumentedFile(ofilepath, "controller", f)
}

func instrumentClientGoForLearn(ifilepath, ofilepath string) {
	f := parseSourceFile(ifilepath, "client")
	_, funcDecl := findFuncDecl(f, "Create")
	index := 0
	if funcDecl != nil {
		instrumentation := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: "NotifyLearnSideEffects", Path: "sonar.client"},
				Args: []dst.Expr{&dst.Ident{Name: "\"create\""}, &dst.Ident{Name: "obj.GetObjectKind().GroupVersionKind().String()"}},
			},
		}
		instrumentation.Decs.End.Append("//sonar")
		insertStmt(&funcDecl.Body.List, index, instrumentation)
	}

	_, funcDecl = findFuncDecl(f, "Update")
	if funcDecl != nil {
		instrumentation := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: "NotifyLearnSideEffects", Path: "sonar.client"},
				Args: []dst.Expr{&dst.Ident{Name: "\"update\""}, &dst.Ident{Name: "obj.GetObjectKind().GroupVersionKind().String()"}},
			},
		}
		instrumentation.Decs.End.Append("//sonar")
		insertStmt(&funcDecl.Body.List, index, instrumentation)
	}

	_, funcDecl = findFuncDecl(f, "Delete")
	if funcDecl != nil {
		instrumentation := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: "NotifyLearnSideEffects", Path: "sonar.client"},
				Args: []dst.Expr{&dst.Ident{Name: "\"delete\""}, &dst.Ident{Name: "obj.GetObjectKind().GroupVersionKind().String()"}},
			},
		}
		instrumentation.Decs.End.Append("//sonar")
		insertStmt(&funcDecl.Body.List, index, instrumentation)
	}

	writeInstrumentedFile(ofilepath, "client", f)
}
