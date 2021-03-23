package sonar

type Response struct {
	Message string
	Ok      bool
	Wait    int
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

type NotifyTimeTravelSideEffectRequest struct {
	Hostname     string
	EventType    string
	ResourceType string
	Name         string
	Namespace    string
}

type NotifyLearnBeforeIndexerWriteRequest struct {
	OperationType string
	Object        string
}

type NotifyLearnBeforeQAddRequest struct {
	Nothing string
}

type NotifyLearnBeforeReconcileRequest struct {
	Nothing string
}

type NotifyLearnAfterReconcileRequest struct {
	Nothing string
}

type NotifyLearnSideEffectsRequest struct {
	SideEffectType string
	Object         string
}
