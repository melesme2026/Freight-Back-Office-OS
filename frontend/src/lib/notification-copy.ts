export const SESSION_REQUIRED_MESSAGE = "Your secure session needs to be refreshed. Please sign in again.";
export const SESSION_EXPIRED_MESSAGE = "Your session ended for security. Please sign in again to continue.";

export const EMAIL_DISABLED_INVITE_MESSAGE =
  "Email delivery is not configured for this workspace. The activation link is ready—copy it and share it with the authorized recipient.";

export const EMAIL_DISABLED_PACKET_MESSAGE =
  "Email delivery is not configured for this workspace. Download the packet or copy the email template and send it from your mail client.";

export function actionCompleted(action: string, nextStep?: string): string {
  return nextStep ? `${action} ${nextStep}` : action;
}

export function actionFailed(action: string, recovery: string): string {
  return `${action} ${recovery}`;
}

export function actionInProgress(action: string): string {
  return `${action} Please keep this window open.`;
}

export function documentUploaded(fileName: string, documentLabel?: string): string {
  const label = documentLabel ? ` as ${documentLabel}` : "";
  return `Document uploaded${label}: ${fileName}. Packet readiness has been refreshed.`;
}

export function documentUploadVerifying(fileName: string): string {
  return `Upload for ${fileName} is taking longer than expected. We are verifying whether the document reached the server.`;
}

export function documentUploadVerificationFailed(fileName?: string): string {
  return fileName
    ? `We could not confirm the upload for ${fileName}. Refresh documents, then retry if it is still missing.`
    : "We could not confirm the upload. Refresh documents, then retry if it is still missing.";
}

export function documentDeleted(fileName: string): string {
  return `Document deleted: ${fileName}. Packet readiness has been refreshed.`;
}

export function documentDeleteVerifying(fileName: string): string {
  return `Delete request for ${fileName} is taking longer than expected. We are verifying the current document list.`;
}

export function documentDeleteVerificationFailed(fileName: string): string {
  return `We could not confirm deletion for ${fileName}. The document was restored in the list; refresh and try again if deletion is still needed.`;
}

export function emailSendFailed(recovery = "Check email configuration, then try again or use the manual download/share option."): string {
  return `Email was not sent. ${recovery}`;
}

export function inviteReady(recipient?: string | null): string {
  return recipient ? `Invite sent to ${recipient}. They can activate their account from the email.` : "Invite is ready. Share the activation instructions with the user.";
}
