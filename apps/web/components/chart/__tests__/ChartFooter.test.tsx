import { render, screen } from "@testing-library/react";
import { ChartFooter } from "../ChartFooter";

describe("ChartFooter", () => {
  it("renders contract code", () => {
    render(
      <ChartFooter
        contract={{ code: "NGF26", expiry: "2026-01-27" }}
        resolution="1d"
        asOf="2026-05-10T00:00:00Z"
      />,
    );
    expect(screen.getByText("NGF26")).toBeInTheDocument();
  });

  it("renders resolution", () => {
    render(
      <ChartFooter
        contract={{ code: "NGF26", expiry: "2026-01-27" }}
        resolution="1d"
        asOf="2026-05-10T00:00:00Z"
      />,
    );
    expect(screen.getByText("1d")).toBeInTheDocument();
  });

  it("renders as of text", () => {
    render(
      <ChartFooter
        contract={{ code: "NGF26", expiry: "2026-01-27" }}
        resolution="1d"
        asOf="2026-05-10T00:00:00Z"
      />,
    );
    expect(screen.getByText(/as of/)).toBeInTheDocument();
  });

  it("renders expiry date", () => {
    render(
      <ChartFooter
        contract={{ code: "NGF26", expiry: "2026-01-27" }}
        resolution="1d"
        asOf="2026-05-10T00:00:00Z"
      />,
    );
    expect(screen.getByText(/expires 2026-01-27/)).toBeInTheDocument();
  });

  it("renders default data source when not provided", () => {
    render(
      <ChartFooter
        contract={{ code: "NGF26", expiry: "2026-01-27" }}
        resolution="1d"
        asOf="2026-05-10T00:00:00Z"
      />,
    );
    expect(screen.getByText("market.mock")).toBeInTheDocument();
  });
});
