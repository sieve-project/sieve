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

// Bad hack: we should report this issue
func auxiliaryImportMap() map[string]string {
	importMap := map[string]string{}
	importMap["k8s.io/klog/v2"] = "klog"
	importMap["github.com/robfig/cron/v3"] = "cron"
	return importMap
}

func parseSourceFile(ifilepath, pkg string, customizedImportMap map[string]string) *dst.File {
	importMap := auxiliaryImportMap()
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

func insertField(list *[]*dst.Field, index int, instrumentation *dst.Field) {
	*list = append((*list)[:index+1], (*list)[index:]...)
	(*list)[index] = instrumentation
}

func writeInstrumentedFile(ofilepath, pkg string, f *dst.File, customizedImportMap map[string]string) {
	importMap := auxiliaryImportMap()
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

func instrumentAnnotatedReconcile(ifilepath, ofilepath, pkg, funName, recvType, stackFrame string) {
	f := parseSourceFile(ifilepath, pkg, map[string]string{})
	_, funcDecl := findFuncDecl(f, funName, recvType)

	if funcDecl != nil {
		index := 0
		beforeReconcileInstrumentation := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: "NotifyLearnBeforeReconcile", Path: "sieve.client"},
				Args: []dst.Expr{&dst.Ident{Name: fmt.Sprintf("\"%s\"", stackFrame)}},
			},
		}
		beforeReconcileInstrumentation.Decs.End.Append("//sieve")
		insertStmt(&funcDecl.Body.List, index, beforeReconcileInstrumentation)

		index += 1
		afterReconcileInstrumentation := &dst.DeferStmt{
			Call: &dst.CallExpr{
				Fun:  &dst.Ident{Name: "NotifyLearnAfterReconcile", Path: "sieve.client"},
				Args: []dst.Expr{&dst.Ident{Name: fmt.Sprintf("\"%s\"", stackFrame)}},
			},
		}
		afterReconcileInstrumentation.Decs.End.Append("//sieve")
		insertStmt(&funcDecl.Body.List, index, afterReconcileInstrumentation)
	} else {
		panic(fmt.Errorf("cannot find function reconcileHandler"))
	}

	writeInstrumentedFile(ofilepath, pkg, f, map[string]string{})
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
		panic(fmt.Errorf("cannot find function HandleDeltas"))
	}

	writeInstrumentedFile(ofilepath, "cache", f, map[string]string{})
}

func instrumentRequestGoForAll(ifilepath, ofilepath, mode string) {
	f := parseSourceFile(ifilepath, "rest", map[string]string{})

	_, _, typeDecl := findTypeDecl(f, "Request")
	if typeDecl != nil {
		log.Println("Find the typeDecl")
		log.Printf("%T\n", typeDecl.Type)
		if structType, ok := typeDecl.Type.(*dst.StructType); ok {
			instrField := &dst.Field{
				Names: []*dst.Ident{&dst.Ident{Name: "obj"}},
				Type:  &dst.Ident{Name: "interface{}"},
			}
			instrField.Decs.End.Append("//sieve")
			insertField(&structType.Fields.List, len(structType.Fields.List)-1, instrField)
		} else {
			panic(fmt.Errorf("request is not struct"))
		}
	} else {
		panic(fmt.Errorf("cannot find type Request"))
	}

	_, funcBodyDecl := findFuncDecl(f, "Body", "*Request")
	if funcBodyDecl != nil {
		instrAssignment := &dst.AssignStmt{
			Lhs: []dst.Expr{&dst.Ident{Name: "r.obj"}},
			Rhs: []dst.Expr{&dst.Ident{Name: "obj"}},
			Tok: token.ASSIGN,
		}
		instrAssignment.Decs.End.Append("//sieve")
		insertStmt(&funcBodyDecl.Body.List, 0, instrAssignment)
	}

	_, funcDecl := findFuncDecl(f, "Do", "*Request")
	funNameBefore := "Notify" + mode + "BeforeRestCall"
	funNameAfter := "Notify" + mode + "AfterRestCall"
	if funcDecl != nil {

		operationIDVar := "operationID"
		instrNotifyLearnBeforeRestWrite := &dst.AssignStmt{
			Lhs: []dst.Expr{&dst.Ident{Name: operationIDVar}},
			Rhs: []dst.Expr{&dst.CallExpr{
				Fun:  &dst.Ident{Name: funNameBefore, Path: "sieve.client"},
				Args: []dst.Expr{&dst.Ident{Name: "r.verb"}, &dst.Ident{Name: "r.pathPrefix"}, &dst.Ident{Name: "r.subpath"}, &dst.Ident{Name: "r.namespace"}, &dst.Ident{Name: "r.namespaceSet"}, &dst.Ident{Name: "r.resource"}, &dst.Ident{Name: "r.resourceName"}, &dst.Ident{Name: "r.subresource"}, &dst.Ident{Name: "r.obj"}},
			}},
			Tok: token.DEFINE,
		}
		instrNotifyLearnBeforeRestWrite.Decs.End.Append("//sieve")
		insertStmt(&funcDecl.Body.List, 0, instrNotifyLearnBeforeRestWrite)

		instruIndex := -1
		for index, stmt := range funcDecl.Body.List {
			// log.Printf("%d %T\n", index, stmt)
			if assignStmt, ok := stmt.(*dst.AssignStmt); ok {
				if callExpr, ok := assignStmt.Rhs[0].(*dst.CallExpr); ok {
					if selectorExpr, ok := callExpr.Fun.(*dst.SelectorExpr); ok {
						if xIdent, ok := selectorExpr.X.(*dst.Ident); ok {
							if xIdent.Name == "r" && selectorExpr.Sel.Name == "request" {
								instruIndex = index + 1
								break
							}
						}
					}
				}
			}
		}
		if instruIndex == -1 {
			panic(fmt.Errorf("cannot find definition of result"))
		}

		instrResultGet := &dst.AssignStmt{
			Lhs: []dst.Expr{&dst.Ident{Name: "resultObj"}, &dst.Ident{Name: "decodingError"}},
			Tok: token.DEFINE,
			Rhs: []dst.Expr{&dst.CallExpr{
				Fun:  &dst.Ident{Name: "result.Get"},
				Args: []dst.Expr{},
			}},
		}
		instrResultGet.Decs.End.Append("//sieve")
		insertStmt(&funcDecl.Body.List, instruIndex, instrResultGet)

		instrNotifyLearnAfterRestWrite := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: funNameAfter, Path: "sieve.client"},
				Args: []dst.Expr{&dst.Ident{Name: operationIDVar}, &dst.Ident{Name: "r.verb"}, &dst.Ident{Name: "r.pathPrefix"}, &dst.Ident{Name: "r.subpath"}, &dst.Ident{Name: "r.namespace"}, &dst.Ident{Name: "r.namespaceSet"}, &dst.Ident{Name: "r.resource"}, &dst.Ident{Name: "r.resourceName"}, &dst.Ident{Name: "r.subresource"}, &dst.Ident{Name: "resultObj"}, &dst.Ident{Name: "decodingError"}, &dst.Ident{Name: "result.Error()"}},
			},
		}
		instrNotifyLearnAfterRestWrite.Decs.End.Append("//sieve")
		insertStmt(&funcDecl.Body.List, instruIndex+1, instrNotifyLearnAfterRestWrite)
	} else {
		panic(fmt.Errorf("cannot find function Do"))
	}
	writeInstrumentedFile(ofilepath, "rest", f, map[string]string{})
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
				panic(fmt.Errorf("wrong type %s for operator read", etype))
			}

			instrumentationReturn := &dst.ReturnStmt{
				Results: []dst.Expr{&dst.Ident{Name: "err"}},
			}
			instrumentationReturn.Decs.End.Append("//sieve")
			funcDecl.Body.List = append(funcDecl.Body.List, instrumentationReturn)
		} else {
			panic(fmt.Errorf("last stmt of %s is not return", etype))
		}
	} else {
		panic(fmt.Errorf("cannot find function %s", etype))
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

func instrumentStoreGoForAll(ifilepath, ofilepath, mode string) {
	f := parseSourceFile(ifilepath, "cache", map[string]string{})
	instrumentCacheGetForAll(f, mode)
	instrumentCacheListForAll(f, mode)
	instrumentCacheByIndexForAll(f, mode)
	writeInstrumentedFile(ofilepath, "cache", f, map[string]string{})
}

func instrumentCacheGetForAll(f *dst.File, mode string) {
	funNameBefore := "Notify" + mode + "BeforeCacheGet"
	funNameAfter := "Notify" + mode + "AfterCacheGet"

	_, funcDecl := findFuncDecl(f, "GetByKey", "*cache")
	if funcDecl == nil {
		panic("instrumentStoreGo error")
	}

	instrumentationBeforeCacheGet := &dst.ExprStmt{
		X: &dst.CallExpr{
			Fun:  &dst.Ident{Name: funNameBefore, Path: "sieve.client"},
			Args: []dst.Expr{&dst.Ident{Name: "key"}, &dst.Ident{Name: "c.cacheStorage.List()"}},
		},
	}
	instrumentationBeforeCacheGet.Decs.End.Append("//sieve")
	insertStmt(&funcDecl.Body.List, 0, instrumentationBeforeCacheGet)

	instrumentationAfterCacheGet := &dst.ExprStmt{
		X: &dst.CallExpr{
			Fun:  &dst.Ident{Name: funNameAfter, Path: "sieve.client"},
			Args: []dst.Expr{&dst.Ident{Name: "key"}, &dst.Ident{Name: "item"}, &dst.Ident{Name: "exists"}},
		},
	}
	instrumentationAfterCacheGet.Decs.End.Append("//sieve")
	insertStmt(&funcDecl.Body.List, 2, instrumentationAfterCacheGet)
}

func instrumentCacheListForAll(f *dst.File, mode string) {
	funNameBefore := "Notify" + mode + "BeforeCacheList"
	funNameAfter := "Notify" + mode + "AfterCacheList"

	_, funcDecl := findFuncDecl(f, "List", "*cache")
	if funcDecl == nil {
		panic("instrumentStoreGo error")
	}

	instrumentationBeforeCacheList := &dst.ExprStmt{
		X: &dst.CallExpr{
			Fun:  &dst.Ident{Name: funNameBefore, Path: "sieve.client"},
			Args: []dst.Expr{&dst.Ident{Name: "c.cacheStorage.List()"}},
		},
	}
	instrumentationBeforeCacheList.Decs.End.Append("//sieve")
	insertStmt(&funcDecl.Body.List, 0, instrumentationBeforeCacheList)

	if returnStmt, ok := funcDecl.Body.List[len(funcDecl.Body.List)-1].(*dst.ReturnStmt); ok {
		modifiedInstruction := &dst.AssignStmt{
			Lhs: []dst.Expr{&dst.Ident{Name: "items"}},
			Tok: token.DEFINE,
			Rhs: returnStmt.Results,
		}
		modifiedInstruction.Decs.End.Append("//sieve")
		funcDecl.Body.List[len(funcDecl.Body.List)-1] = modifiedInstruction

		instrumentationAfterCacheList := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: funNameAfter, Path: "sieve.client"},
				Args: []dst.Expr{&dst.Ident{Name: "items"}, &dst.Ident{Name: "nil"}},
			},
		}
		instrumentationAfterCacheList.Decs.End.Append("//sieve")
		funcDecl.Body.List = append(funcDecl.Body.List, instrumentationAfterCacheList)

		instrumentationReturn := &dst.ReturnStmt{
			Results: []dst.Expr{&dst.Ident{Name: "items"}},
		}
		instrumentationReturn.Decs.End.Append("//sieve")
		funcDecl.Body.List = append(funcDecl.Body.List, instrumentationReturn)
	} else {
		panic("last stmt is not return")
	}
}

func instrumentCacheByIndexForAll(f *dst.File, mode string) {
	funNameBefore := "Notify" + mode + "BeforeCacheList"
	funNameAfter := "Notify" + mode + "AfterCacheList"

	_, funcDecl := findFuncDecl(f, "ByIndex", "*cache")
	if funcDecl == nil {
		panic("instrumentStoreGo error")
	}

	instrumentationBeforeCacheList := &dst.ExprStmt{
		X: &dst.CallExpr{
			Fun:  &dst.Ident{Name: funNameBefore, Path: "sieve.client"},
			Args: []dst.Expr{&dst.Ident{Name: "c.cacheStorage.List()"}},
		},
	}
	instrumentationBeforeCacheList.Decs.End.Append("//sieve")
	insertStmt(&funcDecl.Body.List, 0, instrumentationBeforeCacheList)

	if returnStmt, ok := funcDecl.Body.List[len(funcDecl.Body.List)-1].(*dst.ReturnStmt); ok {
		modifiedInstruction := &dst.AssignStmt{
			Lhs: []dst.Expr{&dst.Ident{Name: "items"}, &dst.Ident{Name: "err"}},
			Tok: token.DEFINE,
			Rhs: returnStmt.Results,
		}
		modifiedInstruction.Decs.End.Append("//sieve")
		funcDecl.Body.List[len(funcDecl.Body.List)-1] = modifiedInstruction

		instrumentationAfterCacheList := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: funNameAfter, Path: "sieve.client"},
				Args: []dst.Expr{&dst.Ident{Name: "items"}, &dst.Ident{Name: "err"}},
			},
		}
		instrumentationAfterCacheList.Decs.End.Append("//sieve")
		funcDecl.Body.List = append(funcDecl.Body.List, instrumentationAfterCacheList)

		instrumentationReturn := &dst.ReturnStmt{
			Results: []dst.Expr{&dst.Ident{Name: "items"}, &dst.Ident{Name: "err"}},
		}
		instrumentationReturn.Decs.End.Append("//sieve")
		funcDecl.Body.List = append(funcDecl.Body.List, instrumentationReturn)
	} else {
		panic("last stmt is not return")
	}
}
