import React from "react";

import { DataAppRuntime } from "./DataAppRuntime.jsx";
import { DashboardContent } from "./content/dashboard/DashboardContent.jsx";
import { ReportContent } from "./content/report/ReportContent.jsx";

export function App({ reviewedSnapshot, hosted = false }) {
  return (
    <DataAppRuntime
      reviewedSnapshot={reviewedSnapshot}
      DashboardContent={DashboardContent}
      ReportContent={ReportContent}
      hosted={hosted}
      staticDemo={!hosted}
    />
  );
}
