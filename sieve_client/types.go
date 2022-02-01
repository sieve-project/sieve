package sieve

type Response struct {
	Message string
	Ok      bool
	Number  int
}

type EchoRequest struct {
	Text string
}

type NotifyStaleStateBeforeProcessEventRequest struct {
	EventType    string
	ResourceType string
	Hostname     string
}

type NotifyStaleStateCrucialEventRequest struct {
	Hostname  string
	EventType string
	Object    string
}

type NotifyStaleStateRestartPointRequest struct {
	Hostname     string
	EventType    string
	ResourceType string
	Name         string
	Namespace    string
}

type NotifyStaleStateAfterSideEffectsRequest struct {
	SideEffectID   int
	SideEffectType string
	Object         string
	ResourceType   string
	Error          string
}

type NotifyUnobsrStateAfterSideEffectsRequest struct {
	SideEffectID   int
	SideEffectType string
	Object         string
	ResourceType   string
	Error          string
}

type NotifyUnobsrStateBeforeIndexerWriteRequest struct {
	OperationType string
	Object        string
	ResourceType  string
}

type NotifyUnobsrStateBeforeInformerCacheReadRequest struct {
	OperationType string
	ResourceType  string
	Name          string
	Namespace     string
}

type NotifyUnobsrStateAfterInformerCacheReadRequest struct {
	OperationType string
	ResourceType  string
	Name          string
	Namespace     string
}

type NotifyUnobsrStateAfterIndexerWriteRequest struct {
	OperationType string
	Object        string
	ResourceType  string
}

type NotifyIntmdStateAfterSideEffectsRequest struct {
	SideEffectID   int
	SideEffectType string
	Object         string
	ResourceType   string
	ReconcilerType string
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
	ReconcilerName string
}

type NotifyLearnAfterReconcileRequest struct {
	ReconcilerName string
}

type NotifyLearnBeforeSideEffectsRequest struct {
	SideEffectType string
}

type NotifyLearnAfterSideEffectsRequest struct {
	SideEffectID   int
	SideEffectType string
	Object         string
	ResourceType   string
	ReconcilerType string
	Error          string
}

type NotifyLearnAfterOperatorGetRequest struct {
	FromCache      bool
	ResourceType   string
	Namespace      string
	Name           string
	Object         string
	ReconcilerType string
	Error          string
}

type NotifyLearnAfterOperatorListRequest struct {
	FromCache      bool
	ResourceType   string
	ObjectList     string
	ReconcilerType string
	Error          string
}

type NotifyIntmdStateAfterOperatorGetRequest struct {
	ResourceType   string
	Namespace      string
	Name           string
	Object         string
	ReconcilerType string
	Error          string
}

type NotifyIntmdStateAfterOperatorListRequest struct {
	ResourceType   string
	ObjectList     string
	ReconcilerType string
	Error          string
}
