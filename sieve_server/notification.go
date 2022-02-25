package main

type TriggerNotification interface {
	getBlockingCh() chan string
}

type TimeoutNotification struct {
	conditionName string
}

func (tn *TimeoutNotification) getBlockingCh() chan string {
	return nil
}

type ObjectCreateNotification struct {
	resourceKey  string
	observedWhen string
	observedBy   string
	blockingCh   chan string
}

func (ocn *ObjectCreateNotification) getBlockingCh() chan string {
	return ocn.blockingCh
}

type ObjectDeleteNotification struct {
	resourceKey  string
	observedWhen string
	observedBy   string
	blockingCh   chan string
}

func (odn *ObjectDeleteNotification) getBlockingCh() chan string {
	return odn.blockingCh
}

type ObjectUpdateNotification struct {
	resourceKey   string
	observedWhen  string
	observedBy    string
	prevState     map[string]interface{}
	curState      map[string]interface{}
	fieldKeyMask  map[string]struct{}
	fieldPathMask map[string]struct{}
	blockingCh    chan string
}

func (oun *ObjectUpdateNotification) getBlockingCh() chan string {
	return oun.blockingCh
}
