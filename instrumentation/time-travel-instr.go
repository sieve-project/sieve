package main

import (
	"github.com/dave/dst"
)

func instrumentWatchCacheGoForTimeTravel(ifilepath, ofilepath string) {
	f := parseSourceFile(ifilepath, "cacher")

	_, funcDecl := findFuncDecl(f, "processEvent")
	if funcDecl == nil {
		panic("instrumentWatchCacheGo error")
	}

	instrumentationInEventProcesss := &dst.DeferStmt{
		Call: &dst.CallExpr{
			Fun:  &dst.Ident{Name: "NotifyTimeTravelAfterProcessEvent", Path: "sonar.client"},
			Args: []dst.Expr{&dst.Ident{Name: "string(event.Type)"}, &dst.Ident{Name: "key"}, &dst.Ident{Name: "event.Object"}},
		},
	}
	instrumentationInEventProcesss.Decs.End.Append("//sonar")
	insertStmt(&funcDecl.Body.List, 2, instrumentationInEventProcesss)

	writeInstrumentedFile(ofilepath, "cacher", f)
}


func instrumentClientGoForTimeTravel(ifilepath, ofilepath string) {
	f := parseSourceFile(ifilepath, "client")
	_, funcDecl := findFuncDecl(f, "Create")
	index := 0
	if funcDecl != nil {
		instrumentation := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: "NotifyTimeTravelSideEffects", Path: "sonar.client"},
				Args: []dst.Expr{&dst.Ident{Name: "\"create\""}, &dst.Ident{Name: "obj"}},
			},
		}
		instrumentation.Decs.End.Append("//sonar")
		insertStmt(&funcDecl.Body.List, index, instrumentation)
	}

	_, funcDecl = findFuncDecl(f, "Update")
	if funcDecl != nil {
		instrumentation := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: "NotifyTimeTravelSideEffects", Path: "sonar.client"},
				Args: []dst.Expr{&dst.Ident{Name: "\"update\""}, &dst.Ident{Name: "obj"}},
			},
		}
		instrumentation.Decs.End.Append("//sonar")
		insertStmt(&funcDecl.Body.List, index, instrumentation)
	}

	_, funcDecl = findFuncDecl(f, "Delete")
	if funcDecl != nil {
		instrumentation := &dst.ExprStmt{
			X: &dst.CallExpr{
				Fun:  &dst.Ident{Name: "NotifyTimeTravelSideEffects", Path: "sonar.client"},
				Args: []dst.Expr{&dst.Ident{Name: "\"delete\""}, &dst.Ident{Name: "obj"}},
			},
		}
		instrumentation.Decs.End.Append("//sonar")
		insertStmt(&funcDecl.Body.List, index, instrumentation)
	}

	writeInstrumentedFile(ofilepath, "client", f)
}
