import React, { useState, useEffect, useMemo } from 'react';
import './AdminDashboard.css';
import {
    getAdminCenters,
    getAdminUsers,
    updateAdminCenter,
    updateAdminUser
} from '../../services/adminService';

export default function AdminDashboard() {
    const [activeTab, setActiveTab] = useState('overview');
    const [centers, setCenters] = useState([]);
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Edit Modal State
    const [editingCenter, setEditingCenter] = useState(null);
    const [isUpdating, setIsUpdating] = useState(false);

    // User Update State
    const [updatingUserId, setUpdatingUserId] = useState(null);

    // Users Filter State
    const [userSearchTerm, setUserSearchTerm] = useState('');
    const [userRoleFilter, setUserRoleFilter] = useState('');

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        setError(null);

        try {
            const [fetchedCenters, fetchedUsers] = await Promise.all([
                getAdminCenters(),
                getAdminUsers()
            ]);

            setCenters(fetchedCenters || []);
            setUsers(fetchedUsers || []);
        } catch (err) {
            console.error(err);
            setError(
                'Failed to load admin data. Please check your connection.'
            );
        } finally {
            setLoading(false);
        }
    };

    // -------------------------------------------------------------
    // OVERVIEW CALCULATIONS
    // -------------------------------------------------------------

    const totalCenters = centers.length;
    const totalFarmers = users.filter(
        u => u.role === 'farmer'
    ).length;

    const totalStaff = users.filter(
        u => u.role === 'procurement'
    ).length;

    const totalAdmins = users.filter(
        u => u.role === 'admin'
    ).length;

    // -------------------------------------------------------------
    // CROP PRICES DERIVATION
    // -------------------------------------------------------------

    const cropPrices = useMemo(() => {
        return centers
            .filter(c => c.crop_type)
            .map(c => ({
                id: c.id,
                centerName: c.name,
                crop: c.crop_type,
                mspRate: c.msp_rate
            }))
            .sort((a, b) => a.crop.localeCompare(b.crop));
    }, [centers]);

    // -------------------------------------------------------------
    // USERS FILTERING
    // -------------------------------------------------------------

    const filteredUsers = useMemo(() => {
        return users.filter(u => {
            const matchesRole = userRoleFilter
                ? u.role === userRoleFilter
                : true;

            const search = userSearchTerm.toLowerCase();

            const matchesSearch =
                (u.name &&
                    u.name.toLowerCase().includes(search)) ||
                (u.phone &&
                    u.phone.toLowerCase().includes(search)) ||
                (u.id &&
                    u.id.toLowerCase().includes(search));

            return matchesRole && matchesSearch;
        });
    }, [users, userSearchTerm, userRoleFilter]);

    // -------------------------------------------------------------
    // EDIT CENTER HANDLERS
    // -------------------------------------------------------------

    const handleEditClick = (center) => {
        setEditingCenter({ ...center });
    };

    const handleEditChange = (e) => {
        const { name, value, type, checked } = e.target;

        setEditingCenter(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    const handleEditSubmit = async (e) => {
        e.preventDefault();

        if (!editingCenter) return;

        setIsUpdating(true);
        setError(null);

        try {
            const updates = {
                name: editingCenter.name,
                location: editingCenter.location,
                crop_type: editingCenter.crop_type,
                msp_rate: Number(editingCenter.msp_rate),
                open_date: editingCenter.open_date,
                close_date: editingCenter.close_date,
                daily_capacity_kg: Number(
                    editingCenter.daily_capacity_kg
                ),
                is_active: Boolean(editingCenter.is_active)
            };

            const updatedCenter = await updateAdminCenter(
                editingCenter.id,
                updates
            );

            // Replace only the edited center.
            // This keeps its original position in the list.
            setCenters(prevCenters =>
                prevCenters.map(center =>
                    center.id === editingCenter.id
                        ? updatedCenter
                        : center
                )
            );

            setEditingCenter(null);
        } catch (err) {
            console.error('UPDATE CENTER ERROR:', err);

            const message =
                err?.body?.detail ||
                'Failed to update center.';

            setError(message);
        } finally {
            setIsUpdating(false);
        }
    };

    // -------------------------------------------------------------
    // USER STATUS HANDLER
    // -------------------------------------------------------------

    const handleToggleUserStatus = async (user) => {
        setUpdatingUserId(user.id);
        setError(null);

        try {
            const updatedUser = await updateAdminUser(user.id, {
                is_active: !user.is_active
            });

            // Replace only the updated user.
            // This keeps the user in the same position.
            setUsers(prevUsers =>
                prevUsers.map(existingUser =>
                    existingUser.id === user.id
                        ? updatedUser
                        : existingUser
                )
            );
        } catch (err) {
            console.error('UPDATE USER ERROR:', err);

            const message =
                err?.body?.detail ||
                'Failed to update user status.';

            setError(message);
        } finally {
            setUpdatingUserId(null);
        }
    };

    // -------------------------------------------------------------
    // RENDER HELPERS
    // -------------------------------------------------------------

    const renderTabNav = () => (
        <nav className="admin-dash__nav">
            <button
                className={`admin-dash__nav-btn ${activeTab === 'overview'
                    ? 'admin-dash__nav-btn--active'
                    : ''
                    }`}
                onClick={() => setActiveTab('overview')}
            >
                Overview
            </button>

            <button
                className={`admin-dash__nav-btn ${activeTab === 'centers'
                    ? 'admin-dash__nav-btn--active'
                    : ''
                    }`}
                onClick={() => setActiveTab('centers')}
            >
                Procurement Centers
            </button>

            <button
                className={`admin-dash__nav-btn ${activeTab === 'users'
                    ? 'admin-dash__nav-btn--active'
                    : ''
                    }`}
                onClick={() => setActiveTab('users')}
            >
                Users
            </button>

            <button
                className={`admin-dash__nav-btn ${activeTab === 'prices'
                    ? 'admin-dash__nav-btn--active'
                    : ''
                    }`}
                onClick={() => setActiveTab('prices')}
            >
                Crop Prices
            </button>
        </nav>
    );

    const renderOverview = () => (
        <div className="admin-dash__overview-grid">
            <div className="admin-dash__summary-card">
                <h3>Total Centers</h3>
                <div className="admin-dash__summary-value">
                    {totalCenters}
                </div>
            </div>

            <div className="admin-dash__summary-card">
                <h3>Total Farmers</h3>
                <div className="admin-dash__summary-value">
                    {totalFarmers}
                </div>
            </div>

            <div className="admin-dash__summary-card">
                <h3>Total Staff</h3>
                <div className="admin-dash__summary-value">
                    {totalStaff}
                </div>
            </div>

            <div className="admin-dash__summary-card">
                <h3>Total Admins</h3>
                <div className="admin-dash__summary-value">
                    {totalAdmins}
                </div>
            </div>
        </div>
    );

    const renderCenters = () => (
        <div className="admin-dash__panel">
            <h2>Manage Procurement Centers</h2>

            <div className="admin-dash__table-wrapper">
                <table className="admin-dash__table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Location</th>
                            <th>Crop</th>
                            <th>MSP Rate</th>
                            <th>Dates</th>
                            <th>Capacity</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>

                    <tbody>
                        {centers.map(c => (
                            <tr key={c.id}>
                                <td>
                                    <strong>{c.name}</strong>
                                </td>

                                <td>{c.location}</td>

                                <td>{c.crop_type}</td>

                                <td>₹{c.msp_rate}</td>

                                <td>
                                    {c.open_date} to {c.close_date}
                                </td>

                                <td>
                                    {c.daily_capacity_kg} kg
                                </td>

                                <td>
                                    <span
                                        className={`admin-dash__badge ${c.is_active
                                            ? 'admin-dash__badge--active'
                                            : 'admin-dash__badge--inactive'
                                            }`}
                                    >
                                        {c.is_active
                                            ? 'Active'
                                            : 'Inactive'}
                                    </span>
                                </td>

                                <td className="admin-dash__actions">
                                    <button
                                        className="admin-dash__btn admin-dash__btn--primary"
                                        onClick={() =>
                                            handleEditClick(c)
                                        }
                                    >
                                        Edit
                                    </button>

                                    <button
                                        className="admin-dash__btn admin-dash__btn--disabled"
                                        disabled
                                        title="Delete coming soon"
                                    >
                                        Delete
                                    </button>
                                </td>
                            </tr>
                        ))}

                        {centers.length === 0 && (
                            <tr>
                                <td
                                    colSpan="8"
                                    className="admin-dash__empty"
                                >
                                    No procurement centers found.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );

    const renderUsers = () => (
        <div className="admin-dash__panel">
            <h2>User Management</h2>

            <div className="admin-dash__filters">
                <input
                    type="text"
                    placeholder="Search by name, phone, or ID..."
                    value={userSearchTerm}
                    onChange={(e) =>
                        setUserSearchTerm(e.target.value)
                    }
                    className="admin-dash__input"
                />

                <select
                    value={userRoleFilter}
                    onChange={(e) =>
                        setUserRoleFilter(e.target.value)
                    }
                    className="admin-dash__select"
                >
                    <option value="">All Roles</option>
                    <option value="admin">Admin</option>
                    <option value="procurement">
                        Procurement
                    </option>
                    <option value="farmer">Farmer</option>
                </select>
            </div>

            <div className="admin-dash__table-wrapper">
                <table className="admin-dash__table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Phone</th>
                            <th>Role</th>
                            <th>Center ID</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>

                    <tbody>
                        {filteredUsers.map(u => (
                            <tr key={u.id}>
                                <td>
                                    {u.name || '—'}
                                </td>

                                <td>
                                    {u.phone || '—'}
                                </td>

                                <td>
                                    <span
                                        className={`admin-dash__badge admin-dash__badge--role-${u.role}`}
                                    >
                                        {u.role}
                                    </span>
                                </td>

                                <td className="admin-dash__mono">
                                    {u.center_id
                                        ? u.center_id.substring(0, 8) +
                                        '...'
                                        : '—'}
                                </td>

                                <td>
                                    <span
                                        className={`admin-dash__badge ${u.is_active
                                            ? 'admin-dash__badge--active'
                                            : 'admin-dash__badge--inactive'
                                            }`}
                                    >
                                        {u.is_active
                                            ? 'Active'
                                            : 'Inactive'}
                                    </span>
                                </td>

                                <td className="admin-dash__actions">
                                    <button
                                        className={`admin-dash__btn ${u.is_active
                                            ? 'admin-dash__btn--disabled'
                                            : 'admin-dash__btn--success'
                                            }`}
                                        onClick={() =>
                                            handleToggleUserStatus(u)
                                        }
                                        disabled={
                                            updatingUserId === u.id
                                        }
                                    >
                                        {updatingUserId === u.id
                                            ? 'Updating...'
                                            : u.is_active
                                                ? 'Deactivate'
                                                : 'Activate'}
                                    </button>
                                </td>
                            </tr>
                        ))}

                        {filteredUsers.length === 0 && (
                            <tr>
                                <td
                                    colSpan="6"
                                    className="admin-dash__empty"
                                >
                                    No users found.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );

    const renderCropPrices = () => (
        <div className="admin-dash__panel">
            <h2>Crop Prices (MSP)</h2>

            <p className="admin-dash__help-text">
                Note: MSP rates are configured per procurement center.
                To edit these, go to the Procurement Centers tab.
            </p>

            <div className="admin-dash__table-wrapper">
                <table className="admin-dash__table">
                    <thead>
                        <tr>
                            <th>Crop Type</th>
                            <th>Procurement Center</th>
                            <th>MSP Rate</th>
                        </tr>
                    </thead>

                    <tbody>
                        {cropPrices.map(c => (
                            <tr key={c.id}>
                                <td>
                                    <strong>{c.crop}</strong>
                                </td>

                                <td>{c.centerName}</td>

                                <td className="admin-dash__price">
                                    ₹{c.mspRate}
                                </td>
                            </tr>
                        ))}

                        {cropPrices.length === 0 && (
                            <tr>
                                <td
                                    colSpan="3"
                                    className="admin-dash__empty"
                                >
                                    No crop data found.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );

    const renderEditModal = () => {
        if (!editingCenter) return null;

        return (
            <div className="admin-dash__modal-backdrop">
                <div className="admin-dash__modal">

                    <div className="admin-dash__modal-header">
                        <h3>Edit Procurement Center</h3>

                        <button
                            className="admin-dash__modal-close"
                            onClick={() =>
                                setEditingCenter(null)
                            }
                        >
                            &times;
                        </button>
                    </div>

                    <form
                        onSubmit={handleEditSubmit}
                        className="admin-dash__form"
                    >
                        <div className="admin-dash__form-group">
                            <label>Name</label>

                            <input
                                type="text"
                                name="name"
                                required
                                value={
                                    editingCenter.name || ''
                                }
                                onChange={handleEditChange}
                                className="admin-dash__input"
                            />
                        </div>

                        <div className="admin-dash__form-group">
                            <label>Location</label>

                            <input
                                type="text"
                                name="location"
                                required
                                value={
                                    editingCenter.location || ''
                                }
                                onChange={handleEditChange}
                                className="admin-dash__input"
                            />
                        </div>

                        <div className="admin-dash__form-row">
                            <div className="admin-dash__form-group">
                                <label>Crop Type</label>

                                <input
                                    type="text"
                                    name="crop_type"
                                    required
                                    value={
                                        editingCenter.crop_type ||
                                        ''
                                    }
                                    onChange={handleEditChange}
                                    className="admin-dash__input"
                                />
                            </div>

                            <div className="admin-dash__form-group">
                                <label>MSP Rate (₹)</label>

                                <input
                                    type="number"
                                    step="0.01"
                                    min="0"
                                    name="msp_rate"
                                    required
                                    value={
                                        editingCenter.msp_rate ||
                                        ''
                                    }
                                    onChange={handleEditChange}
                                    className="admin-dash__input"
                                />
                            </div>
                        </div>

                        <div className="admin-dash__form-row">
                            <div className="admin-dash__form-group">
                                <label>Open Date</label>

                                <input
                                    type="date"
                                    name="open_date"
                                    value={
                                        editingCenter.open_date ||
                                        ''
                                    }
                                    onChange={handleEditChange}
                                    className="admin-dash__input"
                                />
                            </div>

                            <div className="admin-dash__form-group">
                                <label>Close Date</label>

                                <input
                                    type="date"
                                    name="close_date"
                                    value={
                                        editingCenter.close_date ||
                                        ''
                                    }
                                    onChange={handleEditChange}
                                    className="admin-dash__input"
                                />
                            </div>
                        </div>

                        <div className="admin-dash__form-group">
                            <label>Daily Capacity (kg)</label>

                            <input
                                type="number"
                                min="0"
                                step="1"
                                name="daily_capacity_kg"
                                required
                                value={
                                    editingCenter.daily_capacity_kg ||
                                    ''
                                }
                                onChange={handleEditChange}
                                className="admin-dash__input"
                            />
                        </div>

                        <div className="admin-dash__form-group admin-dash__form-group--checkbox">
                            <label>
                                <input
                                    type="checkbox"
                                    name="is_active"
                                    checked={
                                        !!editingCenter.is_active
                                    }
                                    onChange={handleEditChange}
                                />

                                Is Active
                            </label>
                        </div>

                        <div className="admin-dash__modal-footer">
                            <button
                                type="button"
                                className="admin-dash__btn"
                                onClick={() =>
                                    setEditingCenter(null)
                                }
                                disabled={isUpdating}
                            >
                                Cancel
                            </button>

                            <button
                                type="submit"
                                className="admin-dash__btn admin-dash__btn--success"
                                disabled={isUpdating}
                            >
                                {isUpdating
                                    ? 'Saving...'
                                    : 'Save Changes'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        );
    };

    return (
        <div className="admin-dash">

            <header className="admin-dash__header">
                <h1>Admin Dashboard</h1>
                <p>
                    Platform management and oversight.
                </p>
            </header>

            {error && (
                <div
                    className="admin-dash__alert admin-dash__alert--error"
                    role="alert"
                >
                    {error}
                </div>
            )}

            {renderTabNav()}

            <main className="admin-dash__content">
                {loading ? (
                    <div className="admin-dash__loading">
                        <div className="admin-dash__skeleton">
                            Loading admin data...
                        </div>
                    </div>
                ) : (
                    <>
                        {activeTab === 'overview' &&
                            renderOverview()}

                        {activeTab === 'centers' &&
                            renderCenters()}

                        {activeTab === 'users' &&
                            renderUsers()}

                        {activeTab === 'prices' &&
                            renderCropPrices()}
                    </>
                )}
            </main>

            {renderEditModal()}
        </div>
    );
}