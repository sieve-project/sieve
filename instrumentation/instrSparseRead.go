package main

import (
	"go/token"
	"io/ioutil"

	"github.com/dave/dst"
	"github.com/dave/dst/decorator"
	"github.com/dave/dst/decorator/resolver/goast"
)

func instrumentControllerGo(ifilepath, ofilepath string) {
	// We know exactly where and what to instrument.
	// All we need to do is to find the place (function) and inject the code.
	code, err := ioutil.ReadFile(ifilepath)
	check(err)
	dec := decorator.NewDecoratorWithImports(token.NewFileSet(), "controller", goast.New())
	f, err := dec.Parse(code)
	check(err)

	// Reconcile() is invoked in reconcileHandler, so we first find this function.
	_, funcDecl := findFuncDecl(f, "reconcileHandler")
	if funcDecl != nil {
		// Inside reconcileHandler() we find the callsite of Reconcile().
		index, targetStmt := findCallingReconcileIfStmt(funcDecl)
		if targetStmt != nil {
			// Just before the callsite we invoke NotifyBeforeReconcile (RPC to sonar server)
			funcDecl.Body.List = append(funcDecl.Body.List[:index+1], funcDecl.Body.List[index:]...)
			// Generate the expression to call NotifyBeforeReconcile
			instrumentation := &dst.ExprStmt{
				X: &dst.CallExpr{
					Fun:  &dst.Ident{Name: "NotifyBeforeReconcile", Path: "sonar.client"},
					Args: []dst.Expr{&dst.Ident{Name: "c.Name"}},
				},
			}
			instrumentation.Decs.Start.Append("//sonar: NotifyBeforeReconcile")
			funcDecl.Body.List[index] = instrumentation
		}
	}

	// Find Start function
	_, funcDecl = findFuncDecl(f, "Start")
	if funcDecl != nil {
		// Find the place where queue is made
		index, targetStmt := findCallingMakeQueue(funcDecl)
		if targetStmt != nil {
			// Inject after making queue
			index = index + 1
			funcDecl.Body.List = append(funcDecl.Body.List[:index+1], funcDecl.Body.List[index:]...)
			// Generate the expression to call NotifyBeforeMakeQ
			instrumentation := &dst.ExprStmt{
				X: &dst.CallExpr{
					Fun:  &dst.Ident{Name: "NotifyBeforeMakeQ", Path: "sonar.client"},
					Args: []dst.Expr{&dst.Ident{Name: "c.Queue"}, &dst.Ident{Name: "c.Name"}},
				},
			}
			instrumentation.Decs.Start.Append("//sonar: NotifyBeforeMakeQ")
			funcDecl.Body.List[index] = instrumentation
		}
	}

	writeInstrumentedFile("controller", ofilepath, f)
}

func findCallingReconcileIfStmt(funcDecl *dst.FuncDecl) (int, *dst.IfStmt) {
	for i, stmt := range funcDecl.Body.List {
		if ifStmt, ok := stmt.(*dst.IfStmt); ok {
			if assignStmt, ok := ifStmt.Init.(*dst.AssignStmt); ok {
				if callExpr, ok := assignStmt.Rhs[0].(*dst.CallExpr); ok {
					if selectorExpr, ok := callExpr.Fun.(*dst.SelectorExpr); ok {
						if selectorExpr.Sel.Name == "Reconcile" {
							return i, ifStmt
						}
					}
				}
			}
		}
	}
	return -1, nil
}

func findCallingMakeQueue(funcDecl *dst.FuncDecl) (int, *dst.AssignStmt) {
	for i, stmt := range funcDecl.Body.List {
		if assignStmt, ok := stmt.(*dst.AssignStmt); ok {
			if callExpr, ok := assignStmt.Rhs[0].(*dst.CallExpr); ok {
				if selectorExpr, ok := callExpr.Fun.(*dst.SelectorExpr); ok {
					if selectorExpr.Sel.Name == "MakeQueue" {
						return i, assignStmt
					}
				}
			}
		}
	}
	return -1, nil
}

func instrumentEnqueueGo(ifilepath, ofilepath string) {
	code, err := ioutil.ReadFile(ifilepath)
	check(err)
	dec := decorator.NewDecoratorWithImports(token.NewFileSet(), "handler", goast.New())
	f, err := dec.Parse(code)
	check(err)
	// Instrument before each q.Add()
	instrumentBeforeAdd(f)

	writeInstrumentedFile("handler", ofilepath, f)
}

func instrumentBeforeAdd(f *dst.File) {
	for _, decl := range f.Decls {
		if funcDecl, ok := decl.(*dst.FuncDecl); ok {
			instrumentBeforeAddInList(&funcDecl.Body.List)
		}
	}
}

func instrumentBeforeAddInList(list *[]dst.Stmt) {
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
			instrumentBeforeAddInList(&ifStmt.Body.List)
		case *dst.ForStmt:
			forStmt := stmt.(*dst.ForStmt)
			instrumentBeforeAddInList(&forStmt.Body.List)
		case *dst.RangeStmt:
			rangeStmt := stmt.(*dst.RangeStmt)
			instrumentBeforeAddInList(&rangeStmt.Body.List)
		default:
		}
	}

	for _, index := range toInstrument {
		*list = append((*list)[:index+1], (*list)[index:]...)
		instrumentation := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: "NotifyBeforeQAdd", Path: "sonar.client"},
				Args: []dst.Expr{&dst.Ident{Name: "q"}},
			},
		}
		instrumentation.Decs.Start.Append("//sonar: NotifyBeforeQAdd")
		(*list)[index] = instrumentation
	}
}
