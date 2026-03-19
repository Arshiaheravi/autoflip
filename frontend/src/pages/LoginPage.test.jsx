/**
 * Tests for LoginPage component.
 *
 * Covers: renders, form validation, submit calls login, error display.
 * No real network calls — AuthContext is mocked.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Mock context — useAuth must be jest.fn() so tests can call mockReturnValue.
// Do NOT reference outer variables in the factory (jest.mock is hoisted).
jest.mock('@/lib/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('sonner', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
  Toaster: () => null,
}));

// Mock lucide-react icons so they don't break the renderer
jest.mock('lucide-react', () => ({
  Zap: () => <span data-testid="icon-zap" />,
  Mail: () => <span data-testid="icon-mail" />,
  Lock: () => <span data-testid="icon-lock" />,
  Eye: () => <span data-testid="icon-eye" />,
  EyeOff: () => <span data-testid="icon-eyeoff" />,
  ArrowRight: () => <span data-testid="icon-arrow" />,
  AlertCircle: () => <span data-testid="icon-alert" />,
}));

// Mock shadcn components to avoid missing CSS/config issues
jest.mock('@/components/ui/button', () => ({
  Button: ({ children, ...props }) => <button {...props}>{children}</button>,
}));

jest.mock('@/components/ui/input', () => ({
  Input: (props) => <input {...props} />,
}));

import LoginPage from './LoginPage';

describe('LoginPage', () => {
  let mockLogin;

  beforeEach(() => {
    const { useAuth } = require('@/lib/AuthContext');
    mockLogin = jest.fn().mockResolvedValue({});
    useAuth.mockReturnValue({ login: mockLogin });
  });

  const renderLogin = (props = {}) =>
    render(<LoginPage onSuccess={jest.fn()} switchToSignup={jest.fn()} {...props} />);

  test('renders without crashing', () => {
    renderLogin();
    expect(screen.getByTestId('login-page')).toBeTruthy();
  });

  test('renders email and password inputs', () => {
    renderLogin();
    expect(screen.getByTestId('email-input')).toBeTruthy();
    expect(screen.getByTestId('password-input')).toBeTruthy();
  });

  test('shows error when submitting empty form', async () => {
    renderLogin();
    const submitBtn = screen.getByTestId('login-submit');
    fireEvent.click(submitBtn);
    await waitFor(() => {
      expect(screen.getByText(/please enter your email and password/i)).toBeTruthy();
    });
  });

  test('shows error when only email is filled', async () => {
    renderLogin();
    await userEvent.type(screen.getByTestId('email-input'), 'test@example.com');
    fireEvent.click(screen.getByTestId('login-submit'));
    await waitFor(() => {
      expect(screen.getByText(/please enter your email and password/i)).toBeTruthy();
    });
  });

  test('calls login with trimmed email and password', async () => {
    mockLogin.mockResolvedValue({});
    renderLogin();
    await userEvent.type(screen.getByTestId('email-input'), 'user@test.com');
    await userEvent.type(screen.getByTestId('password-input'), 'securepass');
    fireEvent.click(screen.getByTestId('login-submit'));
    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('user@test.com', 'securepass');
    });
  });

  test('calls onSuccess after successful login', async () => {
    mockLogin.mockResolvedValue({});
    const onSuccess = jest.fn();
    renderLogin({ onSuccess });
    await userEvent.type(screen.getByTestId('email-input'), 'user@test.com');
    await userEvent.type(screen.getByTestId('password-input'), 'securepass');
    fireEvent.click(screen.getByTestId('login-submit'));
    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  test('shows server error message on failed login', async () => {
    const { useAuth } = require('@/lib/AuthContext');
    const failLogin = jest.fn().mockRejectedValue({
      response: { data: { detail: 'Invalid email or password' } },
    });
    useAuth.mockReturnValue({ login: failLogin });
    renderLogin();
    await userEvent.type(screen.getByTestId('email-input'), 'bad@test.com');
    await userEvent.type(screen.getByTestId('password-input'), 'wrongpass');
    fireEvent.click(screen.getByTestId('login-submit'));
    await waitFor(() => {
      expect(screen.getByText(/invalid email or password/i)).toBeTruthy();
    });
  });
});
