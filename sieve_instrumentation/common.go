package main

import (
	"bytes"
	"fmt"
	"go/token"
	"io/ioutil"
	"log"
	"os"
	"strings"

	"github.com/dave/dst"
	"github.com/dave/dst/decorator"
	"github.com/dave/dst/decorator/resolver/goast"
	"github.com/dave/dst/decorator/resolver/guess"
)

const TEST string = "test"
const LEARN string = "learn"
const VANILLA string = "vanilla"

func check(e error) {
	if e != nil {
		panic(e)
	}
}

func findFuncDecl(f *dst.File, funName, recvTypeName string) (int, *dst.FuncDecl) {
	for i, decl := range f.Decls {
		if funcDecl, ok := decl.(*dst.FuncDecl); ok {
			if funcDecl.Recv != nil {
				if funcDecl.Name.Name == funName {
					for _, field := range funcDecl.Recv.List {
						if strings.HasPrefix(recvTypeName, "*") {
							if starExpr, ok := field.Type.(*dst.StarExpr); ok {
								if ident, ok := starExpr.X.(*dst.Ident); ok {
									if ident.Name == recvTypeName[1:] {
										return i, funcDecl
									}
								}
							}
						} else {
							log.Fatal("crash here")
						}
					}
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

func parseSourceFile(ifilepath, pkg string, customizedImportMap map[string]string) *dst.File {
	importMap := map[string]string{}
	importMap["k8s.io/klog/v2"] = "klog"
	for k, v := range customizedImportMap {
		importMap[k] = v
	}
	code, err := ioutil.ReadFile(ifilepath)
	check(err)
	dec := decorator.NewDecoratorWithImports(token.NewFileSet(), pkg, goast.WithResolver(guess.WithMap(importMap)))
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

func writeInstrumentedFile(ofilepath, pkg string, f *dst.File, customizedImportMap map[string]string) {
	importMap := map[string]string{}
	importMap["k8s.io/klog/v2"] = "klog"
	for k, v := range customizedImportMap {
		importMap[k] = v
	}
	res := decorator.NewRestorerWithImports(pkg, guess.WithMap(importMap))
	fres := res.FileRestorer()
	fres.Alias["sieve.client"] = "sieve"

	autoInstrFile, err := os.Create(ofilepath)
	check(err)
	defer autoInstrFile.Close()
	var buf bytes.Buffer
	err = fres.Fprint(&buf, f)
	check(err)
	autoInstrFile.Write(buf.Bytes())
}

func instrumentAnnotatedAPI(ifilepath, ofilepath, module, filePath, pkg, funName, recvTypeName, mode string, customizedImportMap map[string]string, instrumentBefore bool) {
	f := parseSourceFile(ifilepath, pkg, customizedImportMap)
	_, funcDecl := findFuncDecl(f, funName, recvTypeName)
	toCallAfter := "Notify" + mode + "AfterAnnotatedAPICall"

	invocationIDVar := "-1"
	if instrumentBefore {
		invocationIDVar = "invocationIDVar"
	}

	// Instrument after side effect
	instrAfterAPICall := &dst.DeferStmt{
		Call: &dst.CallExpr{
			Fun:  &dst.Ident{Name: toCallAfter, Path: "sieve.client"},
			Args: []dst.Expr{&dst.Ident{Name: invocationIDVar}, &dst.Ident{Name: fmt.Sprintf("\"%s\"", module)}, &dst.Ident{Name: fmt.Sprintf("\"%s\"", filePath)}, &dst.Ident{Name: fmt.Sprintf("\"%s\"", recvTypeName)}, &dst.Ident{Name: fmt.Sprintf("\"%s\"", funName)}},
		},
	}
	instrAfterAPICall.Decs.End.Append("//sieve")
	insertStmt(&funcDecl.Body.List, 0, instrAfterAPICall)

	// Instrument before side effect
	if instrumentBefore {
		toCallBefore := "Notify" + mode + "BeforeAnnotatedAPICall"
		instrBeforeAPICall := &dst.AssignStmt{
			Lhs: []dst.Expr{&dst.Ident{Name: invocationIDVar}},
			Rhs: []dst.Expr{&dst.CallExpr{
				Fun:  &dst.Ident{Name: toCallBefore, Path: "sieve.client"},
				Args: []dst.Expr{&dst.Ident{Name: fmt.Sprintf("\"%s\"", module)}, &dst.Ident{Name: fmt.Sprintf("\"%s\"", filePath)}, &dst.Ident{Name: fmt.Sprintf("\"%s\"", recvTypeName)}, &dst.Ident{Name: fmt.Sprintf("\"%s\"", funName)}},
			}},
			Tok: token.DEFINE,
		}
		instrBeforeAPICall.Decs.End.Append("//sieve")
		insertStmt(&funcDecl.Body.List, 0, instrBeforeAPICall)
	}

	writeInstrumentedFile(ofilepath, pkg, f, customizedImportMap)
}

func instrumentSharedInformerGoForAll(ifilepath, ofilepath, mode string) {
	funNameBefore := "Notify" + mode + "BeforeControllerRecv"
	funNameAfter := "Notify" + mode + "AfterControllerRecv"
	f := parseSourceFile(ifilepath, "cache", map[string]string{})
	_, funcDecl := findFuncDecl(f, "HandleDeltas", "*sharedIndexInformer")
	if funcDecl != nil {
		for _, stmt := range funcDecl.Body.List {
			if rangeStmt, ok := stmt.(*dst.RangeStmt); ok {
				instrBeforeControllerRecv := &dst.AssignStmt{
					Lhs: []dst.Expr{&dst.Ident{Name: "recvID"}},
					Rhs: []dst.Expr{&dst.CallExpr{
						Fun:  &dst.Ident{Name: funNameBefore, Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: "string(d.Type)"}, &dst.Ident{Name: "d.Object"}},
					}},
					Tok: token.DEFINE,
				}
				instrBeforeControllerRecv.Decs.End.Append("//sieve")
				insertStmt(&rangeStmt.Body.List, 0, instrBeforeControllerRecv)

				instrAfterControllerRecv := &dst.ExprStmt{
					X: &dst.CallExpr{
						Fun:  &dst.Ident{Name: funNameAfter, Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: "recvID"}, &dst.Ident{Name: "string(d.Type)"}, &dst.Ident{Name: "d.Object"}},
					},
				}
				instrAfterControllerRecv.Decs.End.Append("//sieve")
				rangeStmt.Body.List = append(rangeStmt.Body.List, instrAfterControllerRecv)
				break
			}
		}
	} else {
		panic(fmt.Errorf("Cannot find function HandleDeltas"))
	}

	writeInstrumentedFile(ofilepath, "cache", f, map[string]string{})
}

func instrumentRequestGoForAll(ifilepath, ofilepath, mode string) {
	f := parseSourceFile(ifilepath, "rest", map[string]string{})
	_, funcDecl := findFuncDecl(f, "Do", "*Request")
	funNameBefore := "Notify" + mode + "BeforeRestCall"
	funNameAfter := "Notify" + mode + "AfterRestCall"
	if funcDecl != nil {
		instruIndex := -1
		for index, stmt := range funcDecl.Body.List {
			log.Printf("%d %T\n", index, stmt)
			if declStmt, ok := stmt.(*dst.DeclStmt); ok {
				if genDecl, ok := declStmt.Decl.(*dst.GenDecl); ok {
					if genDecl.Tok == token.VAR {
						instruIndex = index + 1
						break
					}
				}
			}
		}
		if instruIndex == -1 {
			panic(fmt.Errorf("cannot find definition of result"))
		}

		writeIDVar := "writeID"
		instrNotifyLearnBeforeControllerWrite := &dst.AssignStmt{
			Lhs: []dst.Expr{&dst.Ident{Name: writeIDVar}},
			Rhs: []dst.Expr{&dst.CallExpr{
				Fun:  &dst.Ident{Name: funNameBefore, Path: "sieve.client"},
				Args: []dst.Expr{&dst.Ident{Name: "r.verb"}},
			}},
			Tok: token.DEFINE,
		}
		instrNotifyLearnBeforeControllerWrite.Decs.End.Append("//sieve")
		insertStmt(&funcDecl.Body.List, 0, instrNotifyLearnBeforeControllerWrite)

		instrResultGet := &dst.AssignStmt{
			Lhs: []dst.Expr{&dst.Ident{Name: "objForSieve"}, &dst.Ident{Name: "errForSieve"}},
			Tok: token.DEFINE,
			Rhs: []dst.Expr{&dst.CallExpr{
				Fun:  &dst.Ident{Name: "result.Get"},
				Args: []dst.Expr{},
			}},
		}
		instrResultGet.Decs.End.Append("//sieve")
		insertStmt(&funcDecl.Body.List, instruIndex+2, instrResultGet)

		instrNotifyLearnAfterControllerWrite := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: funNameAfter, Path: "sieve.client"},
				Args: []dst.Expr{&dst.Ident{Name: writeIDVar}, &dst.Ident{Name: "r.verb"}, &dst.Ident{Name: "objForSieve"}, &dst.Ident{Name: "errForSieve"}, &dst.Ident{Name: "result.Error()"}},
			},
		}
		instrNotifyLearnAfterControllerWrite.Decs.End.Append("//sieve")
		insertStmt(&funcDecl.Body.List, instruIndex+3, instrNotifyLearnAfterControllerWrite)
	} else {
		panic(fmt.Errorf("cannot find function Do"))
	}
	writeInstrumentedFile(ofilepath, "rest", f, map[string]string{})
}

func instrumentClientGoForAll(ifilepath, ofilepath, mode string, instrumentBefore bool) {
	f := parseSourceFile(ifilepath, "client", map[string]string{})

	instrumentSideEffect(f, "Create", mode, instrumentBefore, "*client")
	instrumentSideEffect(f, "Update", mode, instrumentBefore, "*client")
	instrumentSideEffect(f, "Delete", mode, instrumentBefore, "*client")
	instrumentSideEffect(f, "DeleteAllOf", mode, instrumentBefore, "*client")
	instrumentSideEffect(f, "Patch", mode, instrumentBefore, "*client")

	instrumentSideEffect(f, "Update", mode, instrumentBefore, "*statusWriter")
	instrumentSideEffect(f, "Patch", mode, instrumentBefore, "*statusWriter")

	instrumentClientRead(f, "Get", mode)
	instrumentClientRead(f, "List", mode)

	writeInstrumentedFile(ofilepath, "client", f, map[string]string{})
}

func instrumentSideEffect(f *dst.File, etype, mode string, instrumentBefore bool, recvTypeName string) {
	funNameBefore := "Notify" + mode + "BeforeControllerWrite"
	funNameAfter := "Notify" + mode + "AfterControllerWrite"
	_, funcDecl := findFuncDecl(f, etype, recvTypeName)
	writeName := etype
	if recvTypeName == "*statusWriter" {
		writeName = "Status" + writeName
	}
	if funcDecl != nil {
		if returnStmt, ok := funcDecl.Body.List[len(funcDecl.Body.List)-1].(*dst.ReturnStmt); ok {
			// Instrument before side effect
			writeIDVar := "-1"
			if instrumentBefore {
				writeIDVar = "writeID"
				instrNotifyLearnBeforeControllerWrite := &dst.AssignStmt{
					Lhs: []dst.Expr{&dst.Ident{Name: writeIDVar}},
					Rhs: []dst.Expr{&dst.CallExpr{
						Fun:  &dst.Ident{Name: funNameBefore, Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: fmt.Sprintf("\"%s\"", writeName)}, &dst.Ident{Name: "obj"}},
					}},
					Tok: token.DEFINE,
				}
				instrNotifyLearnBeforeControllerWrite.Decs.End.Append("//sieve")
				insertStmt(&funcDecl.Body.List, len(funcDecl.Body.List)-1, instrNotifyLearnBeforeControllerWrite)
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
			instrNotifyLearnAfterControllerWrite := &dst.ExprStmt{
				X: &dst.CallExpr{
					Fun:  &dst.Ident{Name: funNameAfter, Path: "sieve.client"},
					Args: []dst.Expr{&dst.Ident{Name: writeIDVar}, &dst.Ident{Name: fmt.Sprintf("\"%s\"", writeName)}, &dst.Ident{Name: "obj"}, &dst.Ident{Name: "err"}},
				},
			}
			instrNotifyLearnAfterControllerWrite.Decs.End.Append("//sieve")
			funcDecl.Body.List = append(funcDecl.Body.List, instrNotifyLearnAfterControllerWrite)

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
				writeIDVar := "-1"
				if instrumentBefore {
					writeIDVar = "writeID"
					instrNotifyLearnBeforeControllerWrite := &dst.AssignStmt{
						Lhs: []dst.Expr{&dst.Ident{Name: writeIDVar}},
						Rhs: []dst.Expr{&dst.CallExpr{
							Fun:  &dst.Ident{Name: funNameBefore, Path: "sieve.client"},
							Args: []dst.Expr{&dst.Ident{Name: fmt.Sprintf("\"%s\"", writeName)}, &dst.Ident{Name: "obj"}},
						}},
						Tok: token.DEFINE,
					}
					instrNotifyLearnBeforeControllerWrite.Decs.End.Append("//sieve")
					insertStmt(&defaultCaseClause.Body, len(defaultCaseClause.Body)-1, instrNotifyLearnBeforeControllerWrite)
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
				instrNotifyLearnAfterControllerWrite := &dst.ExprStmt{
					X: &dst.CallExpr{
						Fun:  &dst.Ident{Name: funNameAfter, Path: "sieve.client"},
						Args: []dst.Expr{&dst.Ident{Name: writeIDVar}, &dst.Ident{Name: fmt.Sprintf("\"%s\"", writeName)}, &dst.Ident{Name: "obj"}, &dst.Ident{Name: "err"}},
					},
				}
				instrNotifyLearnAfterControllerWrite.Decs.End.Append("//sieve")
				defaultCaseClause.Body = append(defaultCaseClause.Body, instrNotifyLearnAfterControllerWrite)

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
	funName := "Notify" + mode + "AfterController" + etype
	_, funcDecl := findFuncDecl(f, etype, "*client")
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
	f := parseSourceFile(ifilepath, "client", map[string]string{})

	instrumentCacheRead(f, "Get", mode)
	instrumentCacheRead(f, "List", mode)

	writeInstrumentedFile(ofilepath, "client", f, map[string]string{})
}

func instrumentCacheRead(f *dst.File, etype, mode string) {
	funName := "Notify" + mode + "AfterController" + etype
	_, funcDecl := findFuncDecl(f, etype, "*delegatingReader")
	if funcDecl == nil {
		// support older version controller-runtime
		_, funcDecl = findFuncDecl(f, etype, "*DelegatingReader")
	}
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
	f := parseSourceFile(ifilepath, "cacher", map[string]string{})

	funNameBefore := "Notify" + mode + "BeforeAPIServerRecv"
	funNameAfter := "Notify" + mode + "AfterAPIServerRecv"

	// TODO: do not hardcode the instrumentationIndex
	instrumentationIndex := 5

	_, funcDecl := findFuncDecl(f, "processEvent", "*watchCache")
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

	writeInstrumentedFile(ofilepath, "cacher", f, map[string]string{})
}
