import { Injectable } from '@angular/core';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { Observable, Subject } from 'rxjs';
import { retry, shareReplay, tap } from 'rxjs/operators';

export interface InferenceData {
    frame_id: number;
    timestamp: number;
    faces: Record<string, any>;
}

@Injectable({
    providedIn: 'root'
})
export class WebsocketService {
    private socket$: WebSocketSubject<any>;
    private readonly WS_URL = 'ws://localhost:8000/ws/stream';

    public inferenceStream$: Observable<InferenceData>;
    public connectionStatus$ = new Subject<boolean>();

    constructor() {
        this.socket$ = webSocket({
            url: this.WS_URL,
            openObserver: {
                next: () => this.connectionStatus$.next(true)
            },
            closeObserver: {
                next: () => this.connectionStatus$.next(false)
            }
        });

        this.inferenceStream$ = this.socket$.pipe(
            retry({ delay: 2000 }), // Auto-reconnect
            shareReplay(1)
        );
    }

    public sendMessage(msg: any): void {
        if (this.socket$) {
            this.socket$.next(msg);
        }
    }
}
