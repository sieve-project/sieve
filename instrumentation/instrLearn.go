package main

import (
	"bytes"
	"go/token"
	"io/ioutil"
	"os"

	"github.com/dave/dst"
	"github.com/dave/dst/decorator"
	"github.com/dave/dst/decorator/resolver/goast"
	"github.com/dave/dst/decorator/resolver/guess"
)

func instrumentSharedInformerGoForLearn(ifilepath, ofilepath string) {
	code, err := ioutil.ReadFile(ifilepath)
	check(err)
	dec := decorator.NewDecoratorWithImports(token.NewFileSet(), "cache", goast.New())
	f, err := dec.Parse(code)
	check(err)

	_, funcDecl := findFuncDecl(f, "HandleDeltas")
	if funcDecl != nil {
		for _, stmt := range funcDecl.Body.List {
			if rangeStmt, ok := stmt.(*dst.RangeStmt); ok {
				index := 0
				rangeStmt.Body.List = append(rangeStmt.Body.List[:index+1], rangeStmt.Body.List[index:]...)
				instrumentation := &dst.ExprStmt{
					X: &dst.CallExpr{
						Fun:  &dst.Ident{Name: "NotifyLearnBeforeIndexerWrite", Path: "sonar.client/pkg/sonar"},
						Args: []dst.Expr{&dst.Ident{Name: "string(d.Type)"}, &dst.Ident{Name: "d.Object"}},
					},
				}
				instrumentation.Decs.End.Append("//sonar")
				rangeStmt.Body.List[index] = instrumentation
				break
			}
		}
	}
	res := decorator.NewRestorerWithImports("cache", guess.New())
	autoInstrFile, err := os.Create(ofilepath)
	check(err)
	defer autoInstrFile.Close()
	var buf bytes.Buffer
	err = res.Fprint(&buf, f)
	autoInstrFile.Write(buf.Bytes())
	check(err)
}

func instrumentControllerGoForLearn(ifilepath, ofilepath string) {
	code, err := ioutil.ReadFile(ifilepath)
	check(err)
	dec := decorator.NewDecoratorWithImports(token.NewFileSet(), "controller", goast.New())
	f, err := dec.Parse(code)
	check(err)

	_, funcDecl := findFuncDecl(f, "reconcileHandler")
	if funcDecl != nil {
		// index, targetIfStmt := findCallingReconcileIfStmtForLearn(funcDecl)
		// if targetIfStmt != nil {
			index := 0
			funcDecl.Body.List = append(funcDecl.Body.List[:index+1], funcDecl.Body.List[index:]...)
			beforeReconcileInstrumentation := &dst.ExprStmt{
				X: &dst.CallExpr{
					Fun:  &dst.Ident{Name: "NotifyLearnBeforeReconcile", Path: "sonar.client/pkg/sonar"},
					Args: []dst.Expr{},
				},
			}
			beforeReconcileInstrumentation.Decs.End.Append("//sonar")
			funcDecl.Body.List[index] = beforeReconcileInstrumentation
		// }

		// index, targetExprStmt := findCallingQueueForgetStmtForLearn(funcDecl)
		// if targetExprStmt != nil {
			index += 1
			funcDecl.Body.List = append(funcDecl.Body.List[:index+1], funcDecl.Body.List[index:]...)
			afterReconcileInstrumentation := &dst.DeferStmt{
				Call: &dst.CallExpr{
					Fun:  &dst.Ident{Name: "NotifyLearnAfterReconcile", Path: "sonar.client/pkg/sonar"},
					Args: []dst.Expr{},
				},
			}
			// instrumentation := &dst.ExprStmt{
			// 	X: &dst.CallExpr{
			// 		Fun:  &dst.Ident{Name: "NotifyLearnAfterReconcile", Path: "sonar.client/pkg/sonar"},
			// 		Args: []dst.Expr{},
			// 	},
			// }
			afterReconcileInstrumentation.Decs.End.Append("//sonar")
			funcDecl.Body.List[index] = afterReconcileInstrumentation
		// }
	}

	res := decorator.NewRestorerWithImports("controller", guess.New())

	autoInstrFile, err := os.Create(ofilepath)
	check(err)
	defer autoInstrFile.Close()
	var buf bytes.Buffer
	err = res.Fprint(&buf, f)
	autoInstrFile.Write(buf.Bytes())
	check(err)
}

func instrumentClientGoForLearn(ifilepath, ofilepath string) {
	code, err := ioutil.ReadFile(ifilepath)
	check(err)
	dec := decorator.NewDecoratorWithImports(token.NewFileSet(), "client", goast.New())
	f, err := dec.Parse(code)
	check(err)

	_, funcDecl := findFuncDecl(f, "Create")
	index := 0
	if funcDecl != nil {
		funcDecl.Body.List = append(funcDecl.Body.List[:index+1], funcDecl.Body.List[index:]...)
		instrumentation := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: "NotifyLearnSideEffects", Path: "sonar.client/pkg/sonar"},
				Args: []dst.Expr{&dst.Ident{Name: "\"create\""}},
			},
		}
		instrumentation.Decs.End.Append("//sonar")
		funcDecl.Body.List[index] = instrumentation
	}

	_, funcDecl = findFuncDecl(f, "Update")
	if funcDecl != nil {
		funcDecl.Body.List = append(funcDecl.Body.List[:index+1], funcDecl.Body.List[index:]...)
		instrumentation := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: "NotifyLearnSideEffects", Path: "sonar.client/pkg/sonar"},
				Args: []dst.Expr{&dst.Ident{Name: "\"update\""}},
			},
		}
		instrumentation.Decs.End.Append("//sonar")
		funcDecl.Body.List[index] = instrumentation
	}

	_, funcDecl = findFuncDecl(f, "Delete")
	if funcDecl != nil {
		funcDecl.Body.List = append(funcDecl.Body.List[:index+1], funcDecl.Body.List[index:]...)
		instrumentation := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: "NotifyLearnSideEffects", Path: "sonar.client/pkg/sonar"},
				Args: []dst.Expr{&dst.Ident{Name: "\"delete\""}},
			},
		}
		instrumentation.Decs.End.Append("//sonar")
		funcDecl.Body.List[index] = instrumentation
	}

	res := decorator.NewRestorerWithImports("client", guess.New())

	autoInstrFile, err := os.Create(ofilepath)
	check(err)
	defer autoInstrFile.Close()
	var buf bytes.Buffer
	err = res.Fprint(&buf, f)
	autoInstrFile.Write(buf.Bytes())
	check(err)
}

// func findCallingReconcileIfStmtForLearn(funcDecl *dst.FuncDecl) (int, *dst.IfStmt) {
// 	for i, stmt := range funcDecl.Body.List {
// 		if ifStmt, ok := stmt.(*dst.IfStmt); ok {
// 			if assignStmt, ok := ifStmt.Init.(*dst.AssignStmt); ok {
// 				if callExpr, ok := assignStmt.Rhs[0].(*dst.CallExpr); ok {
// 					if selectorExpr, ok := callExpr.Fun.(*dst.SelectorExpr); ok {
// 						if selectorExpr.Sel.Name == "Reconcile" {
// 							return i, ifStmt
// 						}
// 					}
// 				}
// 			}
// 		}
// 	}
// 	return -1, nil
// }

// func findCallingQueueForgetStmtForLearn(funcDecl *dst.FuncDecl) (int, *dst.ExprStmt) {
// 	for i, stmt := range funcDecl.Body.List {
// 		if exprStmt, ok := stmt.(*dst.ExprStmt); ok {
// 			if callExpr, ok := exprStmt.X.(*dst.CallExpr); ok {
// 				if selectorExpr, ok := callExpr.Fun.(*dst.SelectorExpr); ok {
// 					if selectorExpr.Sel.Name == "Forget" {
// 						return i, exprStmt
// 					}
// 				}
// 			}
// 		}
// 	}
// 	return -1, nil
// }

func instrumentEnqueueGoForLearn(ifilepath, ofilepath string) {
	code, err := ioutil.ReadFile(ifilepath)
	check(err)
	dec := decorator.NewDecoratorWithImports(token.NewFileSet(), "handler", goast.New())
	f, err := dec.Parse(code)
	check(err)
	// Instrument before each q.Add()
	for _, decl := range f.Decls {
		if funcDecl, ok := decl.(*dst.FuncDecl); ok {
			instrumentBeforeAddInListForLearn(&funcDecl.Body.List)
		}
	}

	res := decorator.NewRestorerWithImports("handler", guess.New())

	autoInstrFile, err := os.Create(ofilepath)
	check(err)
	defer autoInstrFile.Close()
	var buf bytes.Buffer
	err = res.Fprint(&buf, f)
	autoInstrFile.Write(buf.Bytes())
	check(err)
}

func instrumentBeforeAddInListForLearn(list *[]dst.Stmt) {
	var toInstrument []int
	for i, stmt := range *list {
		switch stmt.(type) {
		case *dst.ExprStmt:
			exprStmt := stmt.(*dst.ExprStmt)
			if callExpr, ok := exprStmt.X.(*dst.CallExpr); ok {
				if selectorExpr, ok := callExpr.Fun.(*dst.SelectorExpr); ok {
					if selectorExpr.Sel.Name == "Add" {
						// fmt.Println("find Add")
						toInstrument = append(toInstrument, i)
					}
				}
			}
		case *dst.IfStmt:
			ifStmt := stmt.(*dst.IfStmt)
			instrumentBeforeAddInListForLearn(&ifStmt.Body.List)
		case *dst.ForStmt:
			forStmt := stmt.(*dst.ForStmt)
			instrumentBeforeAddInListForLearn(&forStmt.Body.List)
		case *dst.RangeStmt:
			rangeStmt := stmt.(*dst.RangeStmt)
			instrumentBeforeAddInListForLearn(&rangeStmt.Body.List)
		default:
		}
	}

	for _, index := range toInstrument {
		*list = append((*list)[:index+1], (*list)[index:]...)
		instrumentation := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: "NotifyLearnBeforeQAdd", Path: "sonar.client/pkg/sonar"},
				Args: []dst.Expr{},
			},
		}
		instrumentation.Decs.End.Append("//sonar")
		(*list)[index] = instrumentation
	}
}

