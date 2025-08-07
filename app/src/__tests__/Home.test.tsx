// Home.test.tsx: Test para Home usando React Testing Library

import React from 'react';
import { render, screen } from '@testing-library/react';
import Home from '../pages/Home';

test('muestra botón de escaneo', () => {
  render(<Home />);
  expect(screen.getByText(/Escanear Código/i)).toBeInTheDocument();
});

// Explicación:
// - Verifica que el botón de escaneo esté presente en la pantalla principal.
import React from 'react';
import { render, screen } from '@testing-library/react';
import Home from '../pages/Home';

test('muestra botón de escaneo', () => {
  render(<Home />);
  expect(screen.getByText(/Escanear Código/i)).toBeInTheDocument();
});

