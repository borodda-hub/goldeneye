import { render, screen } from "@testing-library/react";
import { HeaderRow } from "../HeaderRow";
import type { FrontMonth, Instrument, VolRegime } from "@/app/(app)/dashboard/types";

const instrument: Instrument = {
  symbol: "NG",
  name: "Natural Gas",
  currency: "USD",
  unit: "MMBtu",
};

const frontMonth: FrontMonth = {
  contract_code: "NGF26",
  last_price: 3.456,
  change_abs: 0.082,
  change_pct: 2.43,
  as_of: "2026-05-10T14:30:00Z",
};

describe("HeaderRow", () => {
  it("renders instrument symbol", () => {
    render(
      <HeaderRow
        instrument={instrument}
        frontMonth={frontMonth}
        volRegime="normal"
        wsStatus="disconnected"
      />,
    );
    expect(screen.getByText("NG")).toBeInTheDocument();
  });

  it("renders contract code", () => {
    render(
      <HeaderRow
        instrument={instrument}
        frontMonth={frontMonth}
        volRegime="normal"
        wsStatus="disconnected"
      />,
    );
    expect(screen.getByText("NGF26")).toBeInTheDocument();
  });

  it("renders price with 3 decimal places", () => {
    render(
      <HeaderRow
        instrument={instrument}
        frontMonth={frontMonth}
        volRegime="normal"
        wsStatus="disconnected"
      />,
    );
    expect(screen.getByText("3.456")).toBeInTheDocument();
  });

  it("renders vol regime chip", () => {
    render(
      <HeaderRow
        instrument={instrument}
        frontMonth={frontMonth}
        volRegime={"elevated" as VolRegime}
        wsStatus="disconnected"
      />,
    );
    expect(screen.getByText(/VOL: elevated/)).toBeInTheDocument();
  });

  it("shows live price when provided", () => {
    render(
      <HeaderRow
        instrument={instrument}
        frontMonth={frontMonth}
        volRegime="normal"
        livePrice={3.999}
        wsStatus="connected"
      />,
    );
    expect(screen.getByText("3.999")).toBeInTheDocument();
  });
});
