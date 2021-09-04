package sonar

type Response struct {
	Message string
	Ok      bool
	Number  int
}

type EchoRequest struct {
	Text string
}

type NotifySparseReadBeforeMakeQRequest struct {
	QueueID        string
	ControllerName string
}

type NotifySparseReadBeforeQAddRequest struct {
	QueueID string
}

type NotifySparseReadBeforeReconcileRequest struct {
	ControllerName string
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

type NotifyTimeTravelSideEffectsRequest struct {
	SideEffectType string
	Object         string
	ResourceType   string
	Error          string
}

type NotifyObsGapSideEffectsRequest struct {
	SideEffectType string
	Object         string
	ResourceType   string
	Error          string
}

type NotifyAtomVioSideEffectsRequest struct {
	SideEffectType string
	Object         string
	ResourceType   string
	Error          string
	Stack          string
}

type NotifyObsGapBeforeIndexerWriteRequest struct {
	OperationType string
	Object        string
	ResourceType  string
}

type NotifyAtomVioBeforeIndexerWriteRequest struct {
	OperationType string
	Object        string
	ResourceType  string
}

type NotifyObsGapBeforeReconcileRequest struct {
	ControllerName string
}

type NotifyObsGapAfterReconcileRequest struct {
	ControllerName string
}

type NotifyObsGapAfterIndexerWriteRequest struct {
	OperationType string
	Object        string
	ResourceType  string
}

type NotifyLearnBeforeIndexerWriteRequest struct {
	OperationType string
	Object        string
	ResourceType  string
}

type NotifyLearnAfterIndexerWriteRequest struct {
	EventID int
}

type NotifyLearnBeforeQAddRequest struct {
	Nothing string
}

type NotifyLearnBeforeReconcileRequest struct {
	ControllerName string
}

type NotifyLearnAfterReconcileRequest struct {
	ControllerName string
}

type NotifyLearnSideEffectsRequest struct {
	SideEffectType string
	Object         string
	ResourceType   string
	Error          string
}

type NotifyLearnCacheGetRequest struct {
	ResourceType string
	Namespace    string
	Name         string
	Error        string
}

type NotifyLearnCacheListRequest struct {
	ResourceType string
	Error        string
}
