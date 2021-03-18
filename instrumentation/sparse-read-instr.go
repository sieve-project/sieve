package main

import (
	"github.com/dave/dst"
)

func instrumentControllerGo(ifilepath, ofilepath string) {
	// We know exactly where and what to instrument.
	// All we need to do is to find the place (function) and inject the code.
	f := parseSourceFile(ifilepath, "controller")

	// Reconcile() is invoked in reconcileHandler, so we first find this function.
	_, funcDecl := findFuncDecl(f, "reconcileHandler")
	if funcDecl != nil {
		// Inside reconcileHandler() we find the callsite of Reconcile().
		index, targetStmt := findCallingReconcileIfStmt(funcDecl)
		if targetStmt != nil {
			// Generate the expression to call NotifySparseReadBeforeReconcile
			instrumentation := &dst.ExprStmt{
				X: &dst.CallExpr{
					Fun:  &dst.Ident{Name: "NotifySparseReadBeforeReconcile", Path: "sonar.client"},
					Args: []dst.Expr{&dst.Ident{Name: "c.Name"}},
				},
			}
			instrumentation.Decs.End.Append("//sonar")
			// Just before the callsite we invoke NotifySparseReadBeforeReconcile (RPC to sonar server)
			insertStmt(&funcDecl.Body.List, index, instrumentation)
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
			// Generate the expression to call NotifySparseReadBeforeMakeQ
			instrumentation := &dst.ExprStmt{
				X: &dst.CallExpr{
					Fun:  &dst.Ident{Name: "NotifySparseReadBeforeMakeQ", Path: "sonar.client"},
					Args: []dst.Expr{&dst.Ident{Name: "c.Queue"}, &dst.Ident{Name: "c.Name"}},
				},
			}
			instrumentation.Decs.End.Append("//sonar")
			insertStmt(&funcDecl.Body.List, index, instrumentation)
		}
	}

	writeInstrumentedFile(ofilepath, "controller", f)
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
	f := parseSourceFile(ifilepath, "handler")
	// Instrument before each q.Add()
	instrumentBeforeAdd(f)

	writeInstrumentedFile(ofilepath, "handler", f)
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
				Fun:  &dst.Ident{Name: "NotifySparseReadBeforeQAdd", Path: "sonar.client"},
				Args: []dst.Expr{&dst.Ident{Name: "q"}},
			},
		}
		instrumentation.Decs.Start.Append("//sonar: NotifySparseReadBeforeQAdd")
		(*list)[index] = instrumentation
	}
}
