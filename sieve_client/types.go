package sieve

type Response struct {
	Message string
	Ok      bool
	Number  int
}

type EchoRequest struct {
	Text string
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

type NotifyLearnBeforeNonK8sSideEffectsRequest struct {
	RecvTypeName string
	FunName      string
}

type NotifyLearnAfterNonK8sSideEffectsRequest struct {
	SideEffectID   int
	RecvTypeName   string
	FunName        string
	ReconcilerType string
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

type NotifyTestBeforeControllerRecvRequest struct {
	OperationType string
	ResourceKey   string
	Object        string
}

type NotifyTestAfterControllerRecvRequest struct {
	OperationType string
	ResourceKey   string
	Object        string
}

type NotifyTestAfterControllerGetRequest struct {
	ResourceKey    string
	ReconcilerType string
	Object         string
}

type NotifyTestAfterControllerListRequest struct {
	ResourceType   string
	ReconcilerType string
	ObjectList     string
}

type NotifyTestAfterControllerWriteRequest struct {
	WriteID        int
	WriteType      string
	ResourceKey    string
	ReconcilerType string
	Object         string
}
