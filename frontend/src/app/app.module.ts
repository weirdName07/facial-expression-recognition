import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { CameraStreamComponent } from './components/camera-stream/camera-stream.component';
import { EmotionWheelComponent } from './components/emotion-wheel/emotion-wheel.component';
import { FaceCardComponent } from './components/face-card/face-card.component';
import { BioSignalWaveformComponent } from './components/bio-signal-waveform/bio-signal-waveform.component';

@NgModule({
  declarations: [
    AppComponent,
    CameraStreamComponent,
    EmotionWheelComponent,
    FaceCardComponent,
    BioSignalWaveformComponent
  ],
  imports: [
    BrowserModule,
    AppRoutingModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
