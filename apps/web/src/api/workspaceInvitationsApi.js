import axios from "axios";

import {
  WORKSPACE_INVITATIONS_API_URL,
  WORKSPACES_API_URL,
} from "./config";
import { buildWorkspaceHeaders } from "./workspaceContext";

const getAuthHeaders = () => {
  const token = localStorage.getItem("finance-dashboard-token");

  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...buildWorkspaceHeaders(),
  };
};

export const createWorkspaceInvitation = async (workspaceId, payload) => {
  const response = await axios.post(
    `${WORKSPACES_API_URL}/${workspaceId}/invitations`,
    payload,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const getPendingWorkspaceInvitations = async () => {
  const response = await axios.get(
    `${WORKSPACE_INVITATIONS_API_URL}/pending`,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const acceptWorkspaceInvitation = async (invitationId) => {
  const response = await axios.post(
    `${WORKSPACE_INVITATIONS_API_URL}/${invitationId}/accept`,
    {},
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const declineWorkspaceInvitation = async (invitationId) => {
  const response = await axios.post(
    `${WORKSPACE_INVITATIONS_API_URL}/${invitationId}/decline`,
    {},
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const cancelWorkspaceInvitation = async (workspaceId, invitationId) => {
  const response = await axios.delete(
    `${WORKSPACES_API_URL}/${workspaceId}/invitations/${invitationId}`,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const getWorkspacePendingInvitations = async (workspaceId) => {
  const response = await axios.get(
    `${WORKSPACES_API_URL}/${workspaceId}/invitations`,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};
