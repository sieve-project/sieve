package main

import (
	"fmt"
	"go/token"

	"github.com/dave/dst"
)

func instrumentSharedInformerGoForLearn(ifilepath, ofilepath string) {
	f := parseSourceFile(ifilepath, "cache")
	_, funcDecl := findFuncDecl(f, "HandleDeltas")
	if funcDecl != nil {
		for _, stmt := range funcDecl.Body.List {
			if rangeStmt, ok := stmt.(*dst.RangeStmt); ok {
				instrNotifyLearnBeforeIndexerWrite := &dst.AssignStmt{
					Lhs: []dst.Expr{&dst.Ident{Name: "sieveEventID"}},
					Rhs: []dst.Expr{&dst.CallExpr{
						Fun:  &dst.Ident{Name: "NotifyLearnBeforeIndexerWrite", Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: "string(d.Type)"}, &dst.Ident{Name: "d.Object"}},
					}},
					Tok: token.DEFINE,
				}
				instrNotifyLearnBeforeIndexerWrite.Decs.End.Append("//sieve")
				insertStmt(&rangeStmt.Body.List, 0, instrNotifyLearnBeforeIndexerWrite)

				instrNotifyLearnAfterIndexerWrite := &dst.ExprStmt{
					X: &dst.CallExpr{
						Fun:  &dst.Ident{Name: "NotifyLearnAfterIndexerWrite", Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: "sieveEventID"}, &dst.Ident{Name: "d.Object"}},
					},
				}
				instrNotifyLearnAfterIndexerWrite.Decs.End.Append("//sieve")
				rangeStmt.Body.List = append(rangeStmt.Body.List, instrNotifyLearnAfterIndexerWrite)
				break
			}
		}
	} else {
		panic(fmt.Errorf("Cannot find function HandleDeltas"))
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
				Fun:  &dst.Ident{Name: "NotifyLearnBeforeReconcile", Path: "sieve.client"},
				Args: []dst.Expr{&dst.Ident{Name: "c.Name"}},
			},
		}
		beforeReconcileInstrumentation.Decs.End.Append("//sieve")
		insertStmt(&funcDecl.Body.List, index, beforeReconcileInstrumentation)

		index += 1
		afterReconcileInstrumentation := &dst.DeferStmt{
			Call: &dst.CallExpr{
				Fun:  &dst.Ident{Name: "NotifyLearnAfterReconcile", Path: "sieve.client"},
				Args: []dst.Expr{&dst.Ident{Name: "c.Name"}},
			},
		}
		afterReconcileInstrumentation.Decs.End.Append("//sieve")
		insertStmt(&funcDecl.Body.List, index, afterReconcileInstrumentation)
	} else {
		panic(fmt.Errorf("Cannot find function reconcileHandler"))
	}

	writeInstrumentedFile(ofilepath, "controller", f)
}

func instrumentSplitGoForLearn(ifilepath, ofilepath string) {
	f := parseSourceFile(ifilepath, "client")

	instrumentCacheRead(f, "Get")
	instrumentCacheRead(f, "List")

	writeInstrumentedFile(ofilepath, "client", f)
}

func instrumentCacheRead(f *dst.File, etype string) {
	_, funcDecl := findFuncDecl(f, etype)
	if funcDecl != nil {
		if returnStmt, ok := funcDecl.Body.List[len(funcDecl.Body.List)-1].(*dst.ReturnStmt); ok {
			modifiedInstruction := &dst.AssignStmt{
				Lhs: []dst.Expr{&dst.Ident{Name: "err"}},
				Tok: token.DEFINE,
				Rhs: returnStmt.Results,
			}
			modifiedInstruction.Decs.End.Append("//sieve")
			funcDecl.Body.List[len(funcDecl.Body.List)-1] = modifiedInstruction

			if etype == "Get" {
				instrumentationExpr := &dst.ExprStmt{
					X: &dst.CallExpr{
						Fun:  &dst.Ident{Name: "NotifyLearnCacheGet", Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: "\"Get\""}, &dst.Ident{Name: "key"}, &dst.Ident{Name: "obj"}, &dst.Ident{Name: "err"}},
					},
				}
				instrumentationExpr.Decs.End.Append("//sieve")
				funcDecl.Body.List = append(funcDecl.Body.List, instrumentationExpr)
			} else if etype == "List" {
				instrumentationExpr := &dst.ExprStmt{
					X: &dst.CallExpr{
						Fun:  &dst.Ident{Name: "NotifyLearnCacheList", Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: "\"List\""}, &dst.Ident{Name: "list"}, &dst.Ident{Name: "err"}},
					},
				}
				instrumentationExpr.Decs.End.Append("//sieve")
				funcDecl.Body.List = append(funcDecl.Body.List, instrumentationExpr)
			} else {
				panic(fmt.Errorf("Wrong type %s for CacheRead", etype))
			}

			instrumentationReturn := &dst.ReturnStmt{
				Results: []dst.Expr{&dst.Ident{Name: "err"}},
			}
			instrumentationReturn.Decs.End.Append("//sieve")
			funcDecl.Body.List = append(funcDecl.Body.List, instrumentationReturn)
		} else {
			panic(fmt.Errorf("Last stmt of %s is not return", etype))
		}
	} else {
		panic(fmt.Errorf("Cannot find function %s", etype))
	}
}

func instrumentClientGoForLearn(ifilepath, ofilepath string) {
	f := parseSourceFile(ifilepath, "client")

	instrumentSideEffectForLearn(f, "Create")
	instrumentSideEffectForLearn(f, "Update")
	instrumentSideEffectForLearn(f, "Delete")
	instrumentSideEffectForLearn(f, "DeleteAllOf")
	instrumentSideEffectForLearn(f, "Patch")

	writeInstrumentedFile(ofilepath, "client", f)
}

func instrumentSideEffectForLearn(f *dst.File, etype string) {
	funNameBefore := "NotifyLearnBeforeSideEffects"
	funNameAfter := "NotifyLearnAfterSideEffects"
	_, funcDecl := findFuncDecl(f, etype)
	if funcDecl != nil {
		if returnStmt, ok := funcDecl.Body.List[len(funcDecl.Body.List)-1].(*dst.ReturnStmt); ok {
			// Instrument before side effect
			instrNotifyLearnBeforeSideEffect := &dst.AssignStmt{
				Lhs: []dst.Expr{&dst.Ident{Name: "sieveSideEffectID"}},
				Rhs: []dst.Expr{&dst.CallExpr{
					Fun:  &dst.Ident{Name: funNameBefore, Path: "sieve.client"},
					Args: []dst.Expr{&dst.Ident{Name: fmt.Sprintf("\"%s\"", etype)}, &dst.Ident{Name: "obj"}},
				}},
				Tok: token.DEFINE,
			}
			instrNotifyLearnBeforeSideEffect.Decs.End.Append("//sieve")
			insertStmt(&funcDecl.Body.List, len(funcDecl.Body.List)-1, instrNotifyLearnBeforeSideEffect)

			// Change return to assign
			modifiedInstruction := &dst.AssignStmt{
				Lhs: []dst.Expr{&dst.Ident{Name: "err"}},
				Tok: token.DEFINE,
				Rhs: returnStmt.Results,
			}
			modifiedInstruction.Decs.End.Append("//sieve")
			funcDecl.Body.List[len(funcDecl.Body.List)-1] = modifiedInstruction

			// Instrument after side effect
			instrNotifyLearnAfterSideEffect := &dst.ExprStmt{
				X: &dst.CallExpr{
					Fun:  &dst.Ident{Name: funNameAfter, Path: "sieve.client"},
					Args: []dst.Expr{&dst.Ident{Name: "sieveSideEffectID"}, &dst.Ident{Name: fmt.Sprintf("\"%s\"", etype)}, &dst.Ident{Name: "obj"}, &dst.Ident{Name: "err"}},
				},
			}
			instrNotifyLearnAfterSideEffect.Decs.End.Append("//sieve")
			funcDecl.Body.List = append(funcDecl.Body.List, instrNotifyLearnAfterSideEffect)

			// return the error of side effect
			instrumentationReturn := &dst.ReturnStmt{
				Results: []dst.Expr{&dst.Ident{Name: "err"}},
			}
			instrumentationReturn.Decs.End.Append("//sieve")
			funcDecl.Body.List = append(funcDecl.Body.List, instrumentationReturn)
		} else if switchStmt, ok := funcDecl.Body.List[len(funcDecl.Body.List)-1].(*dst.TypeSwitchStmt); ok {
			defaultCaseClause, ok := switchStmt.Body.List[len(switchStmt.Body.List)-1].(*dst.CaseClause)
			if !ok {
				panic(fmt.Errorf("Last stmt in SwitchStmt is not CaseClause"))
			}
			if innerReturnStmt, ok := defaultCaseClause.Body[len(defaultCaseClause.Body)-1].(*dst.ReturnStmt); ok {
				// Instrument before side effect
				instrNotifyLearnBeforeSideEffect := &dst.AssignStmt{
					Lhs: []dst.Expr{&dst.Ident{Name: "sieveSideEffectID"}},
					Rhs: []dst.Expr{&dst.CallExpr{
						Fun:  &dst.Ident{Name: funNameBefore, Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: fmt.Sprintf("\"%s\"", etype)}, &dst.Ident{Name: "obj"}},
					}},
					Tok: token.DEFINE,
				}
				instrNotifyLearnBeforeSideEffect.Decs.End.Append("//sieve")
				insertStmt(&defaultCaseClause.Body, len(defaultCaseClause.Body)-1, instrNotifyLearnBeforeSideEffect)

				// Change return to assign
				modifiedInstruction := &dst.AssignStmt{
					Lhs: []dst.Expr{&dst.Ident{Name: "err"}},
					Tok: token.DEFINE,
					Rhs: innerReturnStmt.Results,
				}
				modifiedInstruction.Decs.End.Append("//sieve")
				defaultCaseClause.Body[len(defaultCaseClause.Body)-1] = modifiedInstruction

				// Instrument after side effect
				instrNotifyLearnAfterSideEffect := &dst.ExprStmt{
					X: &dst.CallExpr{
						Fun:  &dst.Ident{Name: funNameAfter, Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: "sieveSideEffectID"}, &dst.Ident{Name: fmt.Sprintf("\"%s\"", etype)}, &dst.Ident{Name: "obj"}, &dst.Ident{Name: "err"}},
					},
				}
				instrNotifyLearnAfterSideEffect.Decs.End.Append("//sieve")
				defaultCaseClause.Body = append(defaultCaseClause.Body, instrNotifyLearnAfterSideEffect)

				// return the error of side effect
				instrumentationReturn := &dst.ReturnStmt{
					Results: []dst.Expr{&dst.Ident{Name: "err"}},
				}
				instrumentationReturn.Decs.End.Append("//sieve")
				defaultCaseClause.Body = append(defaultCaseClause.Body, instrumentationReturn)
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
