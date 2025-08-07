// Home.tsx: Página principal con botón de escaneo y ejemplo de integración de lector de código de barras

import { IonPage, IonHeader, IonToolbar, IonTitle, IonContent, IonButton, IonToast } from '@ionic/react';
import React, { useState } from 'react';
// Barcode reader para web (usa cámara)
import BarcodeReader from 'react-barcode-reader';

const Home: React.FC = () => {
  const [barcode, setBarcode] = useState<string | null>(null);
  const [showToast, setShowToast] = useState(false);

  const handleScan = (data: string) => {
    setBarcode(data);
    setShowToast(true);
  };

  const handleError = (err: any) => {
    setBarcode("Error al escanear");
    setShowToast(true);
  };

  return (
    <IonPage>
      <IonHeader>
        <IonToolbar>
          <IonTitle>Repuestos App</IonTitle>
        </IonToolbar>
      </IonHeader>
      <IonContent className="ion-padding">
        <BarcodeReader
          onError={handleError}
          onScan={handleScan}
        />
        <IonButton expand="block" onClick={() => setShowToast(true)}>
          Escanear Código
        </IonButton>
        <IonToast
          isOpen={showToast}
          onDidDismiss={() => setShowToast(false)}
          message={barcode ? `Código: ${barcode}` : "Escanear próximamente"}
          duration={2000}
        />
      </IonContent>
    </IonPage>
  );
};

export default Home;

// Explicación:
// - Usa react-barcode-reader para escanear códigos de barras con la cámara.
// - Muestra el resultado en un Toast de Ionic.
import { IonPage, IonHeader, IonToolbar, IonTitle, IonContent, IonButton } from '@ionic/react';

const Home: React.FC = () => (
  <IonPage>
    <IonHeader>
      <IonToolbar>
        <IonTitle>Repuestos App</IonTitle>
      </IonToolbar>
    </IonHeader>
    <IonContent className="ion-padding">
      <IonButton expand="block" onClick={() => alert('Escanear próximamente')}>Escanear Código</IonButton>
    </IonContent>
  </IonPage>
);

export default Home;