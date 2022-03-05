package sieve

type Response struct {
	Message string
	Ok      bool
	Number  int
}

type EchoRequest struct {
	Text string
}

type NotifyLearnBeforeControllerRecvRequest struct {
	OperationType string
	Object        string
	ResourceType  string
}

type NotifyLearnAfterControllerRecvRequest struct {
	EventID int
}

type NotifyLearnBeforeReconcileRequest struct {
	ReconcilerName string
}

type NotifyLearnAfterReconcileRequest struct {
	ReconcilerName string
}

type NotifyLearnBeforeControllerWriteRequest struct {
	SideEffectType string
}

type NotifyLearnAfterControllerWriteRequest struct {
	SideEffectID   int
	SideEffectType string
	Object         string
	ResourceType   string
	ReconcilerType string
	Error          string
}

// type NotifyLearnBeforeNKWriteRequest struct {
// 	RecvTypeName string
// 	FunName      string
// }

// type NotifyLearnAfterNKWriteRequest struct {
// 	SideEffectID   int
// 	RecvTypeName   string
// 	FunName        string
// 	ReconcilerType string
// }

type NotifyLearnBeforeAnnotatedAPICallRequest struct {
	ModuleName     string
	FilePath       string
	ReceiverType   string
	FunName        string
	ReconcilerType string
}

type NotifyLearnAfterAnnotatedAPICallRequest struct {
	InvocationID   int
	ModuleName     string
	FilePath       string
	ReceiverType   string
	FunName        string
	ReconcilerType string
}

type NotifyLearnAfterControllerGetRequest struct {
	FromCache      bool
	ResourceType   string
	Namespace      string
	Name           string
	Object         string
	ReconcilerType string
	Error          string
}

type NotifyLearnAfterControllerListRequest struct {
	FromCache      bool
	ResourceType   string
	ObjectList     string
	ReconcilerType string
	Error          string
}

type NotifyTestBeforeAPIServerRecvRequest struct {
	APIServerHostname string
	OperationType     string
	ResourceKey       string
	Object            string
}

type NotifyTestAfterAPIServerRecvRequest struct {
	APIServerHostname string
	OperationType     string
	ResourceKey       string
	Object            string
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

type NotifyTestBeforeControllerReadPauseRequest struct {
	OperationType string
	ResourceKey   string
	ResourceType  string
}

type NotifyTestAfterControllerReadPauseRequest struct {
	OperationType string
	ResourceKey   string
	ResourceType  string
}

type NotifyTestBeforeAnnotatedAPICallRequest struct {
	ModuleName     string
	FilePath       string
	ReceiverType   string
	FunName        string
	ReconcilerType string
}

type NotifyTestAfterAnnotatedAPICallRequest struct {
	ModuleName     string
	FilePath       string
	ReceiverType   string
	FunName        string
	ReconcilerType string
}
