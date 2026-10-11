package main

import (
	"bytes"
	"fmt"
	"go/token"
	"io/ioutil"
	"log"
	"os"
	"path/filepath"
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
			if funcDecl.Recv == nil && recvTypeName == "" && funcDecl.Name.Name == funName {
				return i, funcDecl
			}
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
	f := parseSourceFile(ifilepath, "cache", map[string]string{})
	_, funcDecl := findFuncDecl(f, "HandleDeltas", "*sharedIndexInformer")
	if funcDecl != nil && instrumentDeltaLoop(funcDecl, mode, false) {
		writeInstrumentedFile(ofilepath, "cache", f, map[string]string{})
		return
	}

	// Newer informers delegate cache updates to controller.go. Hook the updates,
	// not just the informer callbacks, so pauses still precede cache mutation.
	ifilepath = filepath.Join(filepath.Dir(ifilepath), "controller.go")
	ofilepath = filepath.Join(filepath.Dir(ofilepath), "controller.go")
	f = parseSourceFile(ifilepath, "cache", map[string]string{})
	_, funcDecl = findFuncDecl(f, "processDeltas", "")
	if funcDecl == nil || !instrumentDeltaLoop(funcDecl, mode, false) {
		panic("cannot find the processDeltas event loop")
	}
	_, replaceFunc := findFuncDecl(f, "processReplacedAllInfo", "")
	if replaceFunc != nil {
		instrumentAtomicReplacement(replaceFunc, mode)
	}
	_, batchFunc := findFuncDecl(f, "processDeltasInBatch", "")
	if batchFunc != nil && !instrumentDeltaLoop(batchFunc, mode, true) {
		panic("cannot find the processDeltasInBatch event loop")
	}
	writeInstrumentedFile(ofilepath, "cache", f, map[string]string{})
}

func instrumentDeltaLoop(funcDecl *dst.FuncDecl, mode string, batch bool) bool {
	funNameBefore := "Notify" + mode + "BeforeControllerRecv"
	funNameAfter := "Notify" + mode + "AfterControllerRecv"
	for _, stmt := range funcDecl.Body.List {
		if rangeStmt, ok := stmt.(*dst.RangeStmt); ok {
			value, ok := rangeStmt.Value.(*dst.Ident)
			if !ok || value.Name != "d" {
				continue
			}
			if !batch && instrumentAtomicDeltaCases(rangeStmt, mode) {
				return true
			}
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
			if batch {
				// A batch mutates the cache atomically, then calls only successful
				// callbacks. Observe completion there, not while assembling it.
				callbacks := 0
				dst.Inspect(rangeStmt, func(n dst.Node) bool {
					if callback, ok := n.(*dst.FuncLit); ok {
						callback.Body.List = append(callback.Body.List, dst.Clone(instrAfterControllerRecv).(dst.Stmt))
						callbacks++
						return false
					}
					return true
				})
				if callbacks != 3 {
					panic("cannot find the add, update and delete batch callbacks")
				}
			} else {
				rangeStmt.Body.List = append(rangeStmt.Body.List, instrAfterControllerRecv)
			}
			return true
		}
	}
	return false
}

// Parse injected blocks with import resolution so the restorer adds sieve.client.
func instrumentationStatements(source, mode string) []dst.Stmt {
	dec := decorator.NewDecoratorWithImports(token.NewFileSet(), "cache", goast.WithResolver(guess.WithMap(auxiliaryImportMap())))
	f, err := dec.Parse("package cache\nimport sieve \"sieve.client\"\nfunc injected() {\n" + strings.ReplaceAll(source, "$MODE", mode) + "\n}")
	check(err)
	_, fn := findFuncDecl(f, "injected", "")
	return fn.Body.List
}

func instrumentAtomicDeltaCases(loop *dst.RangeStmt, mode string) bool {
	for _, stmt := range loop.Body.List {
		switchStmt, ok := stmt.(*dst.SwitchStmt)
		if !ok {
			continue
		}
		clauses := map[string]*dst.CaseClause{}
		for _, stmt := range switchStmt.Body.List {
			clause := stmt.(*dst.CaseClause)
			for _, expr := range clause.List {
				if name, ok := expr.(*dst.Ident); ok {
					clauses[name.Name] = clause
				}
			}
		}
		if clauses["ReplacedAll"] == nil {
			continue
		}
		for _, name := range []string{"Sync", "Deleted"} {
			clause := clauses[name]
			if clause == nil {
				panic("cannot find ordinary delta case " + name)
			}
			before := instrumentationStatements(`recvID := sieve.Notify$MODEBeforeControllerRecv(string(d.Type), d.Object)`, mode)
			clause.Body = append(before, clause.Body...)
			clause.Body = append(clause.Body, instrumentationStatements(`sieve.Notify$MODEAfterControllerRecv(recvID, string(d.Type), d.Object)`, mode)...)
		}
		syncClause := clauses["SyncAll"]
		if syncClause == nil || clauses["Bookmark"] == nil {
			panic("cannot find SyncAll and Bookmark cases")
		}
		for _, stmt := range syncClause.Body {
			if syncLoop, ok := stmt.(*dst.RangeStmt); ok {
				before := instrumentationStatements(`recvID := sieve.Notify$MODEBeforeControllerRecv(string(Sync), obj)`, mode)
				syncLoop.Body.List = append(before, syncLoop.Body.List...)
				syncLoop.Body.List = append(syncLoop.Body.List, instrumentationStatements(`sieve.Notify$MODEAfterControllerRecv(recvID, string(Sync), obj)`, mode)...)
				// ReplacedAll is observed around the atomic Replace below. Bookmarks
				// advance the store resource version without delivering an object.
				return true
			}
		}
		panic("cannot find the SyncAll callback loop")
	}
	return false
}

func instrumentAtomicReplacement(fn *dst.FuncDecl, mode string) {
	before := instrumentationStatements(`
sieveDeletionRecvIDs := make([]int, len(deletions))
for i, obj := range deletions {
	if obj.Obj != nil {
		sieveDeletionRecvIDs[i] = sieve.Notify$MODEBeforeControllerRecv(string(Deleted), obj.Obj)
	}
}
sieveReplacementRecvIDs := make([]int, len(replacements))
for i, r := range replacements {
	sieveReplacementRecvIDs[i] = sieve.Notify$MODEBeforeControllerRecv(string(Replaced), r.newObj)
}`, mode)
	inserted := false
	callbacks := 0
	for i, stmt := range fn.Body.List {
		if conditional, ok := stmt.(*dst.IfStmt); ok {
			if assign, ok := conditional.Init.(*dst.AssignStmt); ok && len(assign.Rhs) == 1 {
				if call, ok := assign.Rhs[0].(*dst.CallExpr); ok {
					if selector, ok := call.Fun.(*dst.SelectorExpr); ok && selector.Sel.Name == "Replace" {
						// Insert outside Replace: no hook can expose a partially replaced cache.
						fn.Body.List = append(append(fn.Body.List[:i:i], before...), fn.Body.List[i:]...)
						inserted = true
					}
				}
			}
		}
		loop, ok := stmt.(*dst.RangeStmt)
		if !ok {
			continue
		}
		objects, ok := loop.X.(*dst.Ident)
		if !ok {
			continue
		}
		switch objects.Name {
		case "deletions":
			loop.Key = dst.NewIdent("i")
			loop.Body.List = append(loop.Body.List, instrumentationStatements(`
if objToDelete.Obj != nil {
	sieve.Notify$MODEAfterControllerRecv(sieveDeletionRecvIDs[i], string(Deleted), objToDelete.Obj)
}`, mode)...)
			callbacks++
		case "replacements":
			loop.Key = dst.NewIdent("i")
			loop.Body.List = append(loop.Body.List, instrumentationStatements(`sieve.Notify$MODEAfterControllerRecv(sieveReplacementRecvIDs[i], string(Replaced), r.newObj)`, mode)...)
			callbacks++
		}
	}
	if !inserted || callbacks != 2 {
		panic("cannot find the atomic Replace and its callback loops")
	}
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
