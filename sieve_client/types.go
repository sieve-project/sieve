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

type NotifyLearnBeforeRestWriteRequest struct {
}

type NotifyLearnAfterRestWriteRequest struct {
	ControllerOperationID   int
	ControllerOperationType string
	ReconcileFun            string
	ResourceType            string
	Namespace               string
	Name                    string
	ObjectBody              string
	Error                   string
}

type NotifyLearnBeforeRestReadRequest struct {
}

type NotifyLearnAfterRestReadRequest struct {
	ControllerOperationID   int
	ControllerOperationType string
	ReconcileFun            string
	ResourceType            string
	Namespace               string
	Name                    string
	ObjectBody              string
	Error                   string
}

type NotifyLearnBeforeAnnotatedAPICallRequest struct {
	ModuleName   string
	FilePath     string
	ReceiverType string
	FunName      string
	ReconcileFun string
}

type NotifyLearnAfterAnnotatedAPICallRequest struct {
	InvocationID int
	ModuleName   string
	FilePath     string
	ReceiverType string
	FunName      string
	ReconcileFun string
}

type NotifyLearnAfterCacheGetRequest struct {
	ResourceType string
	Namespace    string
	Name         string
	Object       string
	ReconcileFun string
	Error        string
}

type NotifyLearnAfterCacheListRequest struct {
	ResourceType string
	ObjectList   string
	ReconcileFun string
	Error        string
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
	ResourceKey  string
	ReconcileFun string
	Object       string
}

type NotifyTestAfterControllerListRequest struct {
	ResourceType string
	ReconcileFun string
	ObjectList   string
}

type NotifyTestBeforeControllerWriteRequest struct {
	WriteType    string
	ResourceKey  string
	ReconcileFun string
	Object       string
}

type NotifyTestAfterControllerWriteRequest struct {
	WriteType    string
	ResourceKey  string
	ReconcileFun string
	Object       string
}

type NotifyTestBeforeControllerWritePauseRequest struct {
	WriteType   string
	ResourceKey string
}

type NotifyTestAfterControllerWritePauseRequest struct {
	WriteType   string
	ResourceKey string
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
	ModuleName   string
	FilePath     string
	ReceiverType string
	FunName      string
	ReconcileFun string
}

type NotifyTestAfterAnnotatedAPICallRequest struct {
	ModuleName   string
	FilePath     string
	ReceiverType string
	FunName      string
	ReconcileFun string
}
