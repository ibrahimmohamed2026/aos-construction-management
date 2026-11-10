/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

class ConstructionDashboard extends Component {
    static template = "aos_construction_management.ConstructionDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            total_projects: 0,
            active_projects: 0,
            completed_projects: 0,
            on_hold_projects: 0,
            total_boq_value: 0,
            total_billed: 0,
            pending_work_orders: 0,
            pending_requisitions: 0,
            open_quality_checks: 0,
            total_expenses: 0,
            loading: true,
        });
        onWillStart(this.loadData.bind(this));
    }

    async loadData() {
        const [
            totalProjects,
            activeProjects,
            completedProjects,
            onHoldProjects,
            pendingWorkOrders,
            pendingRequisitions,
            openQualityChecks,
            boqRecords,
            billingRecords,
            expenseRecords,
        ] = await Promise.all([
            this.orm.searchCount("construction.project", []),
            this.orm.searchCount("construction.project", [["state", "=", "active"]]),
            this.orm.searchCount("construction.project", [["state", "=", "completed"]]),
            this.orm.searchCount("construction.project", [["state", "=", "on_hold"]]),
            this.orm.searchCount("construction.work.order", [["state", "in", ["draft", "confirmed", "in_progress"]]]),
            this.orm.searchCount("construction.material.requisition", [["state", "in", ["draft", "submitted"]]]),
            this.orm.searchCount("construction.quality.check", [["state", "in", ["draft", "in_progress"]]]),
            this.orm.searchRead("construction.boq", [["state", "=", "approved"]], ["total_amount"]),
            this.orm.searchRead("construction.ra.billing", [["state", "=", "approved"]], ["total_amount"]),
            this.orm.searchRead("construction.expense", [["state", "=", "approved"]], ["amount"]),
        ]);

        this.state.total_projects = totalProjects;
        this.state.active_projects = activeProjects;
        this.state.completed_projects = completedProjects;
        this.state.on_hold_projects = onHoldProjects;
        this.state.pending_work_orders = pendingWorkOrders;
        this.state.pending_requisitions = pendingRequisitions;
        this.state.open_quality_checks = openQualityChecks;
        this.state.total_boq_value = boqRecords.reduce((s, r) => s + (r.total_amount || 0), 0);
        this.state.total_billed = billingRecords.reduce((s, r) => s + (r.total_amount || 0), 0);
        this.state.total_expenses = expenseRecords.reduce((s, r) => s + (r.amount || 0), 0);
        this.state.loading = false;
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat(undefined, {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount);
    }

    openProjects(state) {
        const domain = state ? [["state", "=", state]] : [];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Projects",
            res_model: "construction.project",
            view_mode: "list,kanban,form",
            domain: domain,
        });
    }

    openBOQ() {
        this.action.doAction("aos_construction_management.action_construction_boq");
    }

    openWorkOrders(pending) {
        const domain = pending ? [["state", "in", ["draft", "confirmed", "in_progress"]]] : [];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Work Orders",
            res_model: "construction.work.order",
            view_mode: "list,form",
            domain: domain,
        });
    }

    openRequisitions(pending) {
        const domain = pending ? [["state", "in", ["draft", "submitted"]]] : [];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Material Requisitions",
            res_model: "construction.material.requisition",
            view_mode: "list,form",
            domain: domain,
        });
    }

    openQualityChecks(open) {
        const domain = open ? [["state", "in", ["draft", "in_progress"]]] : [];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Quality Checks",
            res_model: "construction.quality.check",
            view_mode: "list,form",
            domain: domain,
        });
    }

    openExpenses() {
        this.action.doAction("aos_construction_management.action_construction_expense");
    }

    openRABilling() {
        this.action.doAction("aos_construction_management.action_construction_ra_billing");
    }
}

registry.category("actions").add("construction_dashboard", ConstructionDashboard);
