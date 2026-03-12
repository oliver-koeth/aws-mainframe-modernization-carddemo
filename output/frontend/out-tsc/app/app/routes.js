import { JobsPlaceholderComponent } from "./jobs-placeholder.component";
export const routes = [
    {
        path: "",
        pathMatch: "full",
        redirectTo: "jobs",
    },
    {
        path: "jobs",
        component: JobsPlaceholderComponent,
    },
];
