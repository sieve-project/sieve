package main

import (
	"fmt"

	"github.com/dave/dst"
)

func instrumentSharedInformerGoForAtomVio(ifilepath, ofilepath string) {
	f := parseSourceFile(ifilepath, "cache")
	_, funcDecl := findFuncDecl(f, "HandleDeltas")
	if funcDecl != nil {
		for _, stmt := range funcDecl.Body.List {
			if rangeStmt, ok := stmt.(*dst.RangeStmt); ok {
				instrNotifyAtomVioBeforeIndexerWrite := &dst.ExprStmt{
					X: &dst.CallExpr{
						Fun:  &dst.Ident{Name: "NotifyAtomVioBeforeIndexerWrite", Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: "string(d.Type)"}, &dst.Ident{Name: "d.Object"}},
					},
				}
				instrNotifyAtomVioBeforeIndexerWrite.Decs.End.Append("//sieve")
				insertStmt(&rangeStmt.Body.List, 0, instrNotifyAtomVioBeforeIndexerWrite)
				break
			}
		}
	} else {
		panic(fmt.Errorf("Cannot find function HandleDeltas"))
	}

	writeInstrumentedFile(ofilepath, "cache", f)
}

func instrumentClientGoForAtomVio(ifilepath, ofilepath string) {
	funName := "NotifyAtomVioBeforeSideEffects"
	f := parseSourceFile(ifilepath, "client")

	instrumentBeforeSideEffectForAtomVio(f, "Create", funName)
	instrumentBeforeSideEffectForAtomVio(f, "Update", funName)
	instrumentBeforeSideEffectForAtomVio(f, "Delete", funName)
	instrumentBeforeSideEffectForAtomVio(f, "DeleteAllOf", funName)
	instrumentBeforeSideEffectForAtomVio(f, "Patch", funName)

	writeInstrumentedFile(ofilepath, "client", f)
}

func instrumentBeforeSideEffectForAtomVio(f *dst.File, etype, funName string) {
	_, funcDecl := findFuncDecl(f, etype)
	if funcDecl != nil {
		if _, ok := funcDecl.Body.List[len(funcDecl.Body.List)-1].(*dst.ReturnStmt); ok {
			instrumentationExpr := &dst.ExprStmt{
				X: &dst.CallExpr{
					Fun:  &dst.Ident{Name: funName, Path: "sieve.client"},
					Args: []dst.Expr{&dst.Ident{Name: fmt.Sprintf("\"%s\"", etype)}, &dst.Ident{Name: "obj"}},
				},
			}
			instrumentationExpr.Decs.End.Append("//sieve")
			insertStmt(&funcDecl.Body.List, len(funcDecl.Body.List)-1, instrumentationExpr)
		} else if switchStmt, ok := funcDecl.Body.List[len(funcDecl.Body.List)-1].(*dst.TypeSwitchStmt); ok {
			defaultCaseClause, ok := switchStmt.Body.List[len(switchStmt.Body.List)-1].(*dst.CaseClause)
			if !ok {
				panic(fmt.Errorf("Last stmt in SwitchStmt is not CaseClause"))
			}
			if _, ok := defaultCaseClause.Body[len(defaultCaseClause.Body)-1].(*dst.ReturnStmt); ok {
				instrumentationExpr := &dst.ExprStmt{
					X: &dst.CallExpr{
						Fun:  &dst.Ident{Name: funName, Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: fmt.Sprintf("\"%s\"", etype)}, &dst.Ident{Name: "obj"}},
					},
				}
				instrumentationExpr.Decs.End.Append("//sieve")
				insertStmt(&defaultCaseClause.Body, len(defaultCaseClause.Body)-1, instrumentationExpr)
			} else {
				panic(fmt.Errorf("Last stmt inside default case of %s is not return", etype))
			}
		} else {
			panic(fmt.Errorf("Last stmt of %s is neither return nor typeswitch", etype))
		}
	} else {
		panic(fmt.Errorf("Cannot find function %s", etype))
	}
}
