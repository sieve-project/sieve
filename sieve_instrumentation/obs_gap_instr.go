package main

import (
	"fmt"

	"github.com/dave/dst"
)

func instrumentSharedInformerGoForUnobsrState(ifilepath, ofilepath string) {
	f := parseSourceFile(ifilepath, "cache")
	_, funcDecl := findFuncDecl(f, "HandleDeltas", 1)
	if funcDecl != nil {
		for _, stmt := range funcDecl.Body.List {
			if rangeStmt, ok := stmt.(*dst.RangeStmt); ok {
				instrNotifyUnobsrStateBeforeIndexerWrite := &dst.ExprStmt{
					X: &dst.CallExpr{
						Fun:  &dst.Ident{Name: "NotifyUnobsrStateBeforeIndexerWrite", Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: "string(d.Type)"}, &dst.Ident{Name: "d.Object"}},
					},
				}
				instrNotifyUnobsrStateBeforeIndexerWrite.Decs.End.Append("//sieve")
				insertStmt(&rangeStmt.Body.List, 0, instrNotifyUnobsrStateBeforeIndexerWrite)

				instrNotifyUnobsrStateAfterIndexerWrite := &dst.ExprStmt{
					X: &dst.CallExpr{
						Fun:  &dst.Ident{Name: "NotifyUnobsrStateAfterIndexerWrite", Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: "string(d.Type)"}, &dst.Ident{Name: "d.Object"}},
					},
				}
				instrNotifyUnobsrStateAfterIndexerWrite.Decs.End.Append("//sieve")
				rangeStmt.Body.List = append(rangeStmt.Body.List, instrNotifyUnobsrStateAfterIndexerWrite)

				break
			}
		}
		writeInstrumentedFile(ofilepath, "cache", f)
	} else {
		panic(fmt.Errorf("Cannot find function HandleDeltas"))
	}
}

func instrumentInformerCacheGoForUnobsrState(ifilepath, ofilepath string) {
	f := parseSourceFile(ifilepath, "cache")

	instrumentInformerCacheRead(f, "Get", "UnobsrState")
	instrumentInformerCacheRead(f, "List", "UnobsrState")

	writeInstrumentedFile(ofilepath, "cache", f)
}

func instrumentInformerCacheRead(f *dst.File, etype, mode string) {
	funNameBefore := "Notify" + mode + "BeforeInformerCache" + etype
	funNameAfter := "Notify" + mode + "AfterInformerCache" + etype
	_, funcDecl := findFuncDecl(f, etype, 1)
	if funcDecl != nil {
		if _, ok := funcDecl.Body.List[len(funcDecl.Body.List)-1].(*dst.ReturnStmt); ok {
			if etype == "Get" {
				beforeGetInstrumentation := &dst.ExprStmt{
					X: &dst.CallExpr{
						Fun:  &dst.Ident{Name: funNameBefore, Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: "\"Get\""}, &dst.Ident{Name: "key"}, &dst.Ident{Name: "out"}},
					},
				}
				beforeGetInstrumentation.Decs.End.Append("//sieve")
				insertStmt(&funcDecl.Body.List, len(funcDecl.Body.List)-1, beforeGetInstrumentation)

				afterGetInstrumentation := &dst.DeferStmt{
					Call: &dst.CallExpr{
						Fun:  &dst.Ident{Name: funNameAfter, Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: "\"Get\""}, &dst.Ident{Name: "key"}, &dst.Ident{Name: "out"}},
					},
				}
				afterGetInstrumentation.Decs.End.Append("//sieve")
				insertStmt(&funcDecl.Body.List, len(funcDecl.Body.List)-1, afterGetInstrumentation)
			} else if etype == "List" {
				beforeListInstrumentation := &dst.ExprStmt{
					X: &dst.CallExpr{
						Fun:  &dst.Ident{Name: funNameBefore, Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: "\"List\""}, &dst.Ident{Name: "out"}},
					},
				}
				beforeListInstrumentation.Decs.End.Append("//sieve")
				insertStmt(&funcDecl.Body.List, len(funcDecl.Body.List)-1, beforeListInstrumentation)

				afterListInstrumentation := &dst.DeferStmt{
					Call: &dst.CallExpr{
						Fun:  &dst.Ident{Name: funNameAfter, Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: "\"List\""}, &dst.Ident{Name: "out"}},
					},
				}
				afterListInstrumentation.Decs.End.Append("//sieve")
				insertStmt(&funcDecl.Body.List, len(funcDecl.Body.List)-1, afterListInstrumentation)
			} else {
				panic(fmt.Errorf("Wrong type %s for operator read", etype))
			}
		} else {
			panic(fmt.Errorf("Last stmt of %s is not return", etype))
		}
	} else {
		panic(fmt.Errorf("Cannot find function %s", etype))
	}
}
