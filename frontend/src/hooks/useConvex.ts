// Temporarily commented out Convex hooks to avoid build errors
// import { useQuery, useMutation } from "convex/react";
// import { api } from "../../../convex/_generated/api";
// import type { Id } from "../../../convex/_generated/dataModel";

// Type for Convex IDs - accepts both string and typed Id
// type ConvexId<T extends string> = Id<T> | string | null | undefined;

// Placeholder hooks that return null/undefined for now
export const useCreateUser = () => () => Promise.resolve(null);
export const useGetUser = (id: string | undefined) => null;
export const useGetUserByEmail = (email: string | undefined) => null;
export const useListUsers = () => [];
export const useUpdateUser = () => () => Promise.resolve(null);
export const useDeleteUser = () => () => Promise.resolve(null);

// Organization hooks
export const useCreateOrganization = () => () => Promise.resolve(null);
export const useGetOrganization = (id: string | undefined) => null;
export const useGetOrganizationBySlug = (slug: string | undefined) => null;
export const useListOrganizationsForUser = (user_id: string | undefined) => [];
export const useGetOrganizationMembers = (organization_id: string | undefined) => [];

// Campaign hooks
export const useCreateCampaign = () => () => Promise.resolve(null);
export const useGetCampaign = (id: any) => null;
export const useListCampaignsByOrganization = (organization_id: any) => [];
export const useListCampaignsByStatus = (status: string | undefined) => [];
export const useUpdateCampaignStatus = () => () => Promise.resolve(null);
export const useUpdateCampaignBriefData = () => () => Promise.resolve(null);
export const useUpdateCampaignCreativeConcepts = () => () => Promise.resolve(null);
export const useDeleteCampaign = () => () => Promise.resolve(null);

// Deliverable hooks
export const useCreateDeliverable = () => () => Promise.resolve(null);
export const useGetDeliverable = (id: any) => null;
export const useListDeliverablesByCampaign = (campaign_id: any) => [];
export const useListDeliverablesByType = (type: string | undefined) => [];
export const useListDeliverablesByStatus = (status: string | undefined) => [];
export const useUpdateDeliverable = () => () => Promise.resolve(null);
export const useUpdateDeliverableStatus = () => () => Promise.resolve(null);
export const useDeleteDeliverable = () => () => Promise.resolve(null);
export const useSubscribeToDeliverables = (campaign_id: any) => [];

// Conversation hooks
export const useCreateConversation = () => () => Promise.resolve(null);
export const useGetConversation = (id: string | undefined) => null;
export const useListConversationsByOrganization = (organization_id: string | undefined) => [];
export const useListConversationsByCampaign = (campaign_id: string | undefined) => [];
export const useUpdateConversation = () => () => Promise.resolve(null);
export const useDeleteConversation = () => () => Promise.resolve(null);

// Message hooks
export const useCreateMessage = () => () => Promise.resolve(null);
export const useGetMessage = (id: string | undefined) => null;
export const useListMessagesByConversation = (conversation_id: string | undefined) => [];
export const useListMessagesByUser = (user_id: string | undefined) => [];
export const useUpdateMessage = () => () => Promise.resolve(null);
export const useDeleteMessage = () => () => Promise.resolve(null);
export const useAddUserMessage = () => () => Promise.resolve(null);
export const useAddAssistantMessage = () => () => Promise.resolve(null);
export const useAddSystemMessage = () => () => Promise.resolve(null);