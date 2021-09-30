package sieve

type Response struct {
	Message string
	Ok      bool
	Number  int
}

type EchoRequest struct {
	Text string
}

type NotifyTimeTravelBeforeProcessEventRequest struct {
	EventType    string
	ResourceType string
	Hostname     string
}

type NotifyTimeTravelCrucialEventRequest struct {
	Hostname  string
	EventType string
	Object    string
}

type NotifyTimeTravelRestartPointRequest struct {
	Hostname     string
	EventType    string
	ResourceType string
	Name         string
	Namespace    string
}

type NotifyTimeTravelAfterSideEffectsRequest struct {
	SideEffectID   int
	SideEffectType string
	Object         string
	ResourceType   string
	Error          string
}

type NotifyObsGapAfterSideEffectsRequest struct {
	SideEffectID   int
	SideEffectType string
	Object         string
	ResourceType   string
	Error          string
}

type NotifyObsGapBeforeIndexerWriteRequest struct {
	OperationType string
	Object        string
	ResourceType  string
}

type NotifyObsGapBeforeInformerCacheReadRequest struct {
}

type NotifyObsGapAfterInformerCacheReadRequest struct {
}

type NotifyObsGapAfterIndexerWriteRequest struct {
	OperationType string
	Object        string
	ResourceType  string
}

type NotifyAtomVioAfterSideEffectsRequest struct {
	SideEffectID   int
	SideEffectType string
	Object         string
	ResourceType   string
	Error          string
}

type NotifyLearnBeforeIndexerWriteRequest struct {
	OperationType string
	Object        string
	ResourceType  string
}

type NotifyLearnAfterIndexerWriteRequest struct {
	EventID int
}

type NotifyLearnBeforeReconcileRequest struct {
	ControllerName string
	ControllerAddr string
}

type NotifyLearnAfterReconcileRequest struct {
	ControllerName string
	ControllerAddr string
}

type NotifyLearnBeforeSideEffectsRequest struct {
	SideEffectType string
}

type NotifyLearnAfterSideEffectsRequest struct {
	SideEffectID   int
	SideEffectType string
	Object         string
	ResourceType   string
	Error          string
}

type NotifyLearnAfterOperatorGetRequest struct {
	ResourceType string
	Namespace    string
	Name         string
	Object       string
	Error        string
}

type NotifyLearnAfterOperatorListRequest struct {
	ResourceType string
	ObjectList   string
	Error        string
}

type NotifyAtomVioAfterOperatorGetRequest struct {
	ResourceType string
	Namespace    string
	Name         string
	Object       string
	Error        string
}

type NotifyAtomVioAfterOperatorListRequest struct {
	ResourceType string
	ObjectList   string
	Error        string
}
