"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
	createContext,
	useContext,
	useState,
	type ReactNode,
} from "react";

type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";

interface RealtimeContextValue {
	status: ConnectionStatus;
}

const RealtimeContext = createContext<RealtimeContextValue>({
	status: "disconnected",
});

export function useRealtimeContext() {
	return useContext(RealtimeContext);
}

function makeQueryClient() {
	return new QueryClient({
		defaultOptions: {
			queries: {
				staleTime: 30_000,
				retry: 1,
			},
		},
	});
}

let browserQueryClient: QueryClient | undefined;

function getQueryClient() {
	if (typeof window === "undefined") return makeQueryClient();
	if (!browserQueryClient) browserQueryClient = makeQueryClient();
	return browserQueryClient;
}

export function Providers({ children }: { children: ReactNode }) {
	const queryClient = getQueryClient();
	const [status] = useState<ConnectionStatus>("disconnected");

	return (
		<QueryClientProvider client={queryClient}>
			<RealtimeContext.Provider value={{ status }}>
				{children}
			</RealtimeContext.Provider>
		</QueryClientProvider>
	);
}
