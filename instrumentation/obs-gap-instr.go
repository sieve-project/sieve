package main

import (
	"fmt"

	"github.com/dave/dst"
)

func instrumentSharedInformerGoForObsGap(ifilepath, ofilepath string) {
	f := parseSourceFile(ifilepath, "cache")
	_, funcDecl := findFuncDecl(f, "HandleDeltas")
	if funcDecl != nil {
		for _, stmt := range funcDecl.Body.List {
			if rangeStmt, ok := stmt.(*dst.RangeStmt); ok {
				instrNotifyObsGapBeforeIndexerWrite := &dst.ExprStmt{
					X: &dst.CallExpr{
						Fun:  &dst.Ident{Name: "NotifyObsGapBeforeIndexerWrite", Path: "sonar.client"},
						Args: []dst.Expr{&dst.Ident{Name: "string(d.Type)"}, &dst.Ident{Name: "d.Object"}},
					},
				}
				instrNotifyObsGapBeforeIndexerWrite.Decs.End.Append("//sonar")
				insertStmt(&rangeStmt.Body.List, 0, instrNotifyObsGapBeforeIndexerWrite)

				instrNotifyObsGapAfterIndexerWrite := &dst.ExprStmt{
					X: &dst.CallExpr{
						Fun:  &dst.Ident{Name: "NotifyObsGapAfterIndexerWrite", Path: "sonar.client"},
						Args: []dst.Expr{&dst.Ident{Name: "string(d.Type)"}, &dst.Ident{Name: "d.Object"}},
					},
				}
				instrNotifyObsGapAfterIndexerWrite.Decs.End.Append("//sonar")
				rangeStmt.Body.List = append(rangeStmt.Body.List, instrNotifyObsGapAfterIndexerWrite)

				break
			}
		}
	} else {
		panic(fmt.Errorf("Cannot find function HandleDeltas"))
	}

	writeInstrumentedFile(ofilepath, "cache", f)
}

func instrumentControllerGoForObsGap(ifilepath, ofilepath string) {
	f := parseSourceFile(ifilepath, "controller")
	_, funcDecl := findFuncDecl(f, "reconcileHandler")
	if funcDecl != nil {
		index := 0
		beforeReconcileInstrumentation := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: "NotifyObsGapBeforeReconcile", Path: "sonar.client"},
				Args: []dst.Expr{&dst.Ident{Name: "c.Name"}},
			},
		}
		beforeReconcileInstrumentation.Decs.End.Append("//sonar")
		insertStmt(&funcDecl.Body.List, index, beforeReconcileInstrumentation)
	} else {
		panic(fmt.Errorf("Cannot find function reconcileHandler"))
	}

	writeInstrumentedFile(ofilepath, "controller", f)
}
