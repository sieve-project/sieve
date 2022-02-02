package main

import (
	"bytes"
	"fmt"
	"go/token"
	"io/ioutil"
	"os"
	"strings"

	"github.com/dave/dst/decorator/resolver/goast"

	"github.com/dave/dst"
	"github.com/dave/dst/decorator"
	"github.com/dave/dst/decorator/resolver/guess"
)

const STALE_STATE string = "stale-state"
const UNOBSERVED_STATE string = "unobserved-state"
const INTERMEDIATE_STATE string = "intermediate-state"
const LEARN string = "learn"
const VANILLA string = "vanilla"

func check(e error) {
	if e != nil {
		panic(e)
	}
}

func findFuncDecl(f *dst.File, funName string, expectedCnt int) (int, *dst.FuncDecl) {
	cnt := 0
	for i, decl := range f.Decls {
		if funcDecl, ok := decl.(*dst.FuncDecl); ok {
			if funcDecl.Name.Name == funName {
				cnt += 1
				if cnt == expectedCnt {
					return i, funcDecl
				}
			}
		}
	}
	return -1, nil
}

func findTypeDecl(f *dst.File, typeName string) (int, int, *dst.TypeSpec) {
	for i, decl := range f.Decls {
		if genDecl, ok := decl.(*dst.GenDecl); ok && genDecl.Tok == token.TYPE {
			for j, spec := range genDecl.Specs {
				if typeSpec, ok := spec.(*dst.TypeSpec); ok {
					if typeSpec.Name.Name == typeName {
						return i, j, typeSpec
					}
				}
			}
		}
	}
	return -1, -1, nil
}

func parseSourceFile(ifilepath, pkg string) *dst.File {
	code, err := ioutil.ReadFile(ifilepath)
	check(err)
	dec := decorator.NewDecoratorWithImports(token.NewFileSet(), pkg, goast.New())
	f, err := dec.Parse(code)
	check(err)
	return f
}

func insertStmt(list *[]dst.Stmt, index int, instrumentation dst.Stmt) {
	*list = append((*list)[:index+1], (*list)[index:]...)
	(*list)[index] = instrumentation
}

func insertDecl(list *[]dst.Decl, index int, instrumentation dst.Decl) {
	*list = append((*list)[:index+1], (*list)[index:]...)
	(*list)[index] = instrumentation
}

func writeInstrumentedFile(ofilepath, pkg string, f *dst.File) {
	res := decorator.NewRestorerWithImports(pkg, guess.New())
	fres := res.FileRestorer()
	fres.Alias["sieve.client"] = "sieve"
	fres.Alias["k8s.io/klog/v2"] = "klog"

	autoInstrFile, err := os.Create(ofilepath)
	check(err)
	defer autoInstrFile.Close()
	var buf bytes.Buffer
	err = fres.Fprint(&buf, f)
	autoInstrFile.Write(buf.Bytes())
	check(err)
}

func preprocess(path string) {
	read, err := ioutil.ReadFile(path)
	check(err)
	newContents := strings.Replace(string(read), "\"k8s.io/klog/v2\"", "klog \"k8s.io/klog/v2\"", 1)
	err = ioutil.WriteFile(path, []byte(newContents), 0)
	check(err)
}

func instrumentClientGoForAll(ifilepath, ofilepath, mode string, instrumentBefore bool) {
	f := parseSourceFile(ifilepath, "client")

	instrumentSideEffect(f, "Create", mode, instrumentBefore, 1)
	instrumentSideEffect(f, "Update", mode, instrumentBefore, 1)
	instrumentSideEffect(f, "Delete", mode, instrumentBefore, 1)
	instrumentSideEffect(f, "DeleteAllOf", mode, instrumentBefore, 1)
	instrumentSideEffect(f, "Patch", mode, instrumentBefore, 1)

	instrumentSideEffect(f, "Update", mode, instrumentBefore, 2)
	instrumentSideEffect(f, "Patch", mode, instrumentBefore, 2)

	instrumentClientRead(f, "Get", mode)
	instrumentClientRead(f, "List", mode)

	writeInstrumentedFile(ofilepath, "client", f)
}

func instrumentSideEffect(f *dst.File, etype, mode string, instrumentBefore bool, expectedCnt int) {
	funNameBefore := "Notify" + mode + "BeforeSideEffects"
	funNameAfter := "Notify" + mode + "AfterSideEffects"
	_, funcDecl := findFuncDecl(f, etype, expectedCnt)
	writeName := etype
	if expectedCnt == 2 {
		writeName = "Status" + writeName
	}
	if funcDecl != nil {
		if returnStmt, ok := funcDecl.Body.List[len(funcDecl.Body.List)-1].(*dst.ReturnStmt); ok {
			// Instrument before side effect
			sideEffectIDVar := "-1"
			if instrumentBefore {
				sideEffectIDVar = "sieveSideEffectID"
				instrNotifyLearnBeforeSideEffect := &dst.AssignStmt{
					Lhs: []dst.Expr{&dst.Ident{Name: sideEffectIDVar}},
					Rhs: []dst.Expr{&dst.CallExpr{
						Fun:  &dst.Ident{Name: funNameBefore, Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: fmt.Sprintf("\"%s\"", writeName)}, &dst.Ident{Name: "obj"}},
					}},
					Tok: token.DEFINE,
				}
				instrNotifyLearnBeforeSideEffect.Decs.End.Append("//sieve")
				insertStmt(&funcDecl.Body.List, len(funcDecl.Body.List)-1, instrNotifyLearnBeforeSideEffect)
			}

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
					Args: []dst.Expr{&dst.Ident{Name: sideEffectIDVar}, &dst.Ident{Name: fmt.Sprintf("\"%s\"", writeName)}, &dst.Ident{Name: "obj"}, &dst.Ident{Name: "err"}},
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
				sideEffectIDVar := "-1"
				if instrumentBefore {
					sideEffectIDVar = "sieveSideEffectID"
					instrNotifyLearnBeforeSideEffect := &dst.AssignStmt{
						Lhs: []dst.Expr{&dst.Ident{Name: sideEffectIDVar}},
						Rhs: []dst.Expr{&dst.CallExpr{
							Fun:  &dst.Ident{Name: funNameBefore, Path: "sieve.client"},
							Args: []dst.Expr{&dst.Ident{Name: fmt.Sprintf("\"%s\"", writeName)}, &dst.Ident{Name: "obj"}},
						}},
						Tok: token.DEFINE,
					}
					instrNotifyLearnBeforeSideEffect.Decs.End.Append("//sieve")
					insertStmt(&defaultCaseClause.Body, len(defaultCaseClause.Body)-1, instrNotifyLearnBeforeSideEffect)
				}

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
						Args: []dst.Expr{&dst.Ident{Name: sideEffectIDVar}, &dst.Ident{Name: fmt.Sprintf("\"%s\"", writeName)}, &dst.Ident{Name: "obj"}, &dst.Ident{Name: "err"}},
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

func instrumentClientRead(f *dst.File, etype, mode string) {
	funName := "Notify" + mode + "AfterOperator" + etype
	_, funcDecl := findFuncDecl(f, etype, 1)
	if funcDecl != nil {
		if returnStmt, ok := funcDecl.Body.List[len(funcDecl.Body.List)-1].(*dst.ReturnStmt); ok {

			// Change return to assign
			modifiedInstruction := &dst.AssignStmt{
				Lhs: []dst.Expr{&dst.Ident{Name: "err"}},
				Tok: token.DEFINE,
				Rhs: returnStmt.Results,
			}
			modifiedInstruction.Decs.End.Append("//sieve")
			funcDecl.Body.List[len(funcDecl.Body.List)-1] = modifiedInstruction

			// Instrument after client read
			if etype == "Get" {
				instrumentationExpr := &dst.ExprStmt{
					X: &dst.CallExpr{
						Fun:  &dst.Ident{Name: funName, Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: "\"Get\""}, &dst.Ident{Name: "false"}, &dst.Ident{Name: "key"}, &dst.Ident{Name: "obj"}, &dst.Ident{Name: "err"}},
					},
				}
				instrumentationExpr.Decs.End.Append("//sieve")
				funcDecl.Body.List = append(funcDecl.Body.List, instrumentationExpr)
			} else if etype == "List" {
				instrumentationExpr := &dst.ExprStmt{
					X: &dst.CallExpr{
						Fun:  &dst.Ident{Name: funName, Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: "\"List\""}, &dst.Ident{Name: "false"}, &dst.Ident{Name: "obj"}, &dst.Ident{Name: "err"}},
					},
				}
				instrumentationExpr.Decs.End.Append("//sieve")
				funcDecl.Body.List = append(funcDecl.Body.List, instrumentationExpr)
			} else {
				panic(fmt.Errorf("Wrong type %s for operator read", etype))
			}

			// return the error of client read
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

				// Change return to assign
				modifiedInstruction := &dst.AssignStmt{
					Lhs: []dst.Expr{&dst.Ident{Name: "err"}},
					Tok: token.DEFINE,
					Rhs: innerReturnStmt.Results,
				}
				modifiedInstruction.Decs.End.Append("//sieve")
				defaultCaseClause.Body[len(defaultCaseClause.Body)-1] = modifiedInstruction

				// Instrument after client read
				if etype == "Get" {
					instrumentationExpr := &dst.ExprStmt{
						X: &dst.CallExpr{
							Fun:  &dst.Ident{Name: funName, Path: "sieve.client"},
							Args: []dst.Expr{&dst.Ident{Name: "\"Get\""}, &dst.Ident{Name: "false"}, &dst.Ident{Name: "key"}, &dst.Ident{Name: "obj"}, &dst.Ident{Name: "err"}},
						},
					}
					instrumentationExpr.Decs.End.Append("//sieve")
					defaultCaseClause.Body = append(defaultCaseClause.Body, instrumentationExpr)
				} else if etype == "List" {
					instrumentationExpr := &dst.ExprStmt{
						X: &dst.CallExpr{
							Fun:  &dst.Ident{Name: funName, Path: "sieve.client"},
							Args: []dst.Expr{&dst.Ident{Name: "\"List\""}, &dst.Ident{Name: "false"}, &dst.Ident{Name: "obj"}, &dst.Ident{Name: "err"}},
						},
					}
					instrumentationExpr.Decs.End.Append("//sieve")
					defaultCaseClause.Body = append(defaultCaseClause.Body, instrumentationExpr)
				} else {
					panic(fmt.Errorf("Wrong type %s for operator read", etype))
				}

				// return the error of client read
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

func instrumentSplitGoForAll(ifilepath, ofilepath, mode string) {
	f := parseSourceFile(ifilepath, "client")

	instrumentCacheRead(f, "Get", mode)
	instrumentCacheRead(f, "List", mode)

	writeInstrumentedFile(ofilepath, "client", f)
}

func instrumentCacheRead(f *dst.File, etype, mode string) {
	funName := "Notify" + mode + "AfterOperator" + etype
	_, funcDecl := findFuncDecl(f, etype, 1)
	if funcDecl != nil {
		// instrument cache read
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
						Fun:  &dst.Ident{Name: funName, Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: "\"Get\""}, &dst.Ident{Name: "true"}, &dst.Ident{Name: "key"}, &dst.Ident{Name: "obj"}, &dst.Ident{Name: "err"}},
					},
				}
				instrumentationExpr.Decs.End.Append("//sieve")
				funcDecl.Body.List = append(funcDecl.Body.List, instrumentationExpr)
			} else if etype == "List" {
				instrumentationExpr := &dst.ExprStmt{
					X: &dst.CallExpr{
						Fun:  &dst.Ident{Name: funName, Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: "\"List\""}, &dst.Ident{Name: "true"}, &dst.Ident{Name: "list"}, &dst.Ident{Name: "err"}},
					},
				}
				instrumentationExpr.Decs.End.Append("//sieve")
				funcDecl.Body.List = append(funcDecl.Body.List, instrumentationExpr)
			} else {
				panic(fmt.Errorf("Wrong type %s for operator read", etype))
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

func instrumentWatchCacheGoForAll(ifilepath, ofilepath, mode string, instrumentBefore, instrumentAfter bool) {
	f := parseSourceFile(ifilepath, "cacher")

	funNameBefore := "Notify" + mode + "BeforeProcessEvent"
	funNameAfter := "Notify" + mode + "AfterProcessEvent"

	// TODO: do not hardcode the instrumentationIndex
	instrumentationIndex := 5

	_, funcDecl := findFuncDecl(f, "processEvent", 1)
	if funcDecl == nil {
		panic("instrumentWatchCacheGo error")
	}

	if instrumentBefore {
		instrumentationInProcessEventBeforeReconcile := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: funNameBefore, Path: "sieve.client"},
				Args: []dst.Expr{&dst.Ident{Name: "string(event.Type)"}, &dst.Ident{Name: "key"}, &dst.Ident{Name: "event.Object"}},
			},
		}
		instrumentationInProcessEventBeforeReconcile.Decs.End.Append("//sieve")
		insertStmt(&funcDecl.Body.List, instrumentationIndex, instrumentationInProcessEventBeforeReconcile)
	}

	if instrumentAfter {
		instrumentationInProcessEventAfterReconcile := &dst.DeferStmt{
			Call: &dst.CallExpr{
				Fun:  &dst.Ident{Name: funNameAfter, Path: "sieve.client"},
				Args: []dst.Expr{&dst.Ident{Name: "string(event.Type)"}, &dst.Ident{Name: "key"}, &dst.Ident{Name: "event.Object"}},
			},
		}
		instrumentationInProcessEventAfterReconcile.Decs.End.Append("//sieve")
		insertStmt(&funcDecl.Body.List, instrumentationIndex, instrumentationInProcessEventAfterReconcile)
	}

	writeInstrumentedFile(ofilepath, "cacher", f)
}
