import React, { useState, useCallback } from 'react';
import './KanbanBoard.css';

/**
 * KanbanBoard - Drag-and-drop campaign workflow management.
 *
 * Features:
 * - Visual campaign pipeline
 * - Drag-and-drop task movement
 * - Task assignment and priority
 * - Progress tracking
 * - Quick actions (approve, reject, comment)
 */

const DEFAULT_COLUMNS = [
    { id: 'backlog', title: 'Backlog', icon: '📋', color: '#666' },
    { id: 'todo', title: 'To Do', icon: '📝', color: '#6366f1' },
    { id: 'in-progress', title: 'In Progress', icon: '🔄', color: '#f59e0b' },
    { id: 'review', title: 'Review', icon: '👁️', color: '#8b5cf6' },
    { id: 'approved', title: 'Approved', icon: '✅', color: '#10b981' },
    { id: 'published', title: 'Published', icon: '🚀', color: '#ec4899' },
];

const PRIORITY_BADGES = {
    high: { label: 'High', color: '#ef4444' },
    medium: { label: 'Medium', color: '#f59e0b' },
    low: { label: 'Low', color: '#10b981' },
};

const TYPE_ICONS = {
    social_post: '📱',
    email: '✉️',
    blog_post: '📝',
    ad: '📢',
    video: '🎬',
    landing_page: '🌐',
    strategy: '📊',
};

export default function KanbanBoard({
    tasks = [],
    columns = DEFAULT_COLUMNS,
    onTaskMove,
    onTaskClick,
    onTaskEdit,
    onAddTask,
    onDeleteTask,
    campaignName = 'Campaign',
}) {
    const [draggedTask, setDraggedTask] = useState(null);
    const [dragOverColumn, setDragOverColumn] = useState(null);
    const [showAddModal, setShowAddModal] = useState(null); // column id
    const [newTaskTitle, setNewTaskTitle] = useState('');

    // Group tasks by column
    const tasksByColumn = columns.reduce((acc, col) => {
        acc[col.id] = tasks.filter(t => t.status === col.id);
        return acc;
    }, {});

    const handleDragStart = useCallback((e, task) => {
        setDraggedTask(task);
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', task.id);
    }, []);

    const handleDragOver = useCallback((e, columnId) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        setDragOverColumn(columnId);
    }, []);

    const handleDragLeave = useCallback(() => {
        setDragOverColumn(null);
    }, []);

    const handleDrop = useCallback((e, columnId) => {
        e.preventDefault();
        setDragOverColumn(null);

        if (draggedTask && draggedTask.status !== columnId) {
            onTaskMove?.(draggedTask.id, columnId);
        }
        setDraggedTask(null);
    }, [draggedTask, onTaskMove]);

    const handleAddTask = useCallback((columnId) => {
        if (newTaskTitle.trim()) {
            onAddTask?.({
                title: newTaskTitle.trim(),
                status: columnId,
                priority: 'medium',
                type: 'task',
            });
            setNewTaskTitle('');
            setShowAddModal(null);
        }
    }, [newTaskTitle, onAddTask]);

    const getColumnStats = (columnId) => {
        const columnTasks = tasksByColumn[columnId] || [];
        return {
            total: columnTasks.length,
            high: columnTasks.filter(t => t.priority === 'high').length,
        };
    };

    return (
        <div className="kanban-board">
            {/* Header */}
            <div className="kanban-board__header">
                <div className="kanban-board__title">
                    <h2>📋 Workflow</h2>
                    <span className="kanban-board__campaign">{campaignName}</span>
                </div>
                <div className="kanban-board__stats">
                    <span>{tasks.length} tasks</span>
                    <span>•</span>
                    <span>{tasks.filter(t => t.status === 'published').length} published</span>
                </div>
            </div>

            {/* Board */}
            <div className="kanban-board__columns">
                {columns.map(column => {
                    const columnTasks = tasksByColumn[column.id] || [];
                    const stats = getColumnStats(column.id);
                    const isDropTarget = dragOverColumn === column.id;

                    return (
                        <div
                            key={column.id}
                            className={`kanban-column ${isDropTarget ? 'kanban-column--drop-target' : ''}`}
                            onDragOver={(e) => handleDragOver(e, column.id)}
                            onDragLeave={handleDragLeave}
                            onDrop={(e) => handleDrop(e, column.id)}
                        >
                            {/* Column Header */}
                            <div className="kanban-column__header">
                                <div className="kanban-column__title">
                                    <span
                                        className="kanban-column__icon"
                                        style={{ backgroundColor: column.color + '20' }}
                                    >
                                        {column.icon}
                                    </span>
                                    <span>{column.title}</span>
                                    <span className="kanban-column__count">{stats.total}</span>
                                </div>
                                <button
                                    className="kanban-column__add"
                                    onClick={() => setShowAddModal(column.id)}
                                    title="Add task"
                                >
                                    +
                                </button>
                            </div>

                            {/* Tasks */}
                            <div className="kanban-column__tasks">
                                {columnTasks.map(task => {
                                    const priority = PRIORITY_BADGES[task.priority] || PRIORITY_BADGES.medium;
                                    const typeIcon = TYPE_ICONS[task.type] || '📄';
                                    const isDragging = draggedTask?.id === task.id;

                                    return (
                                        <div
                                            key={task.id}
                                            className={`kanban-task ${isDragging ? 'kanban-task--dragging' : ''}`}
                                            draggable
                                            onDragStart={(e) => handleDragStart(e, task)}
                                            onClick={() => onTaskClick?.(task)}
                                        >
                                            {/* Task Header */}
                                            <div className="kanban-task__header">
                                                <span className="kanban-task__type">{typeIcon}</span>
                                                <span
                                                    className="kanban-task__priority"
                                                    style={{ backgroundColor: priority.color }}
                                                    title={priority.label + ' priority'}
                                                />
                                            </div>

                                            {/* Task Content */}
                                            <div className="kanban-task__title">{task.title}</div>

                                            {task.description && (
                                                <div className="kanban-task__description">
                                                    {task.description.substring(0, 80)}
                                                    {task.description.length > 80 ? '...' : ''}
                                                </div>
                                            )}

                                            {/* Task Footer */}
                                            <div className="kanban-task__footer">
                                                {task.assignee && (
                                                    <span className="kanban-task__assignee" title={task.assignee}>
                                                        👤 {task.assignee.split(' ')[0]}
                                                    </span>
                                                )}
                                                {task.dueDate && (
                                                    <span className="kanban-task__due">
                                                        📅 {new Date(task.dueDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                                                    </span>
                                                )}
                                                {task.comments > 0 && (
                                                    <span className="kanban-task__comments">
                                                        💬 {task.comments}
                                                    </span>
                                                )}
                                            </div>

                                            {/* Platform Badge */}
                                            {task.platform && (
                                                <div className="kanban-task__platform">
                                                    {task.platform}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}

                                {/* Empty Column */}
                                {columnTasks.length === 0 && (
                                    <div className="kanban-column__empty">
                                        <p>No tasks</p>
                                        <button
                                            className="kanban-column__empty-add"
                                            onClick={() => setShowAddModal(column.id)}
                                        >
                                            + Add task
                                        </button>
                                    </div>
                                )}
                            </div>

                            {/* Add Task Modal */}
                            {showAddModal === column.id && (
                                <div className="kanban-add-modal">
                                    <input
                                        type="text"
                                        className="kanban-add-modal__input"
                                        placeholder="Task title..."
                                        value={newTaskTitle}
                                        onChange={(e) => setNewTaskTitle(e.target.value)}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter') handleAddTask(column.id);
                                            if (e.key === 'Escape') setShowAddModal(null);
                                        }}
                                        autoFocus
                                    />
                                    <div className="kanban-add-modal__actions">
                                        <button
                                            className="kanban-add-modal__btn kanban-add-modal__btn--primary"
                                            onClick={() => handleAddTask(column.id)}
                                        >
                                            Add
                                        </button>
                                        <button
                                            className="kanban-add-modal__btn"
                                            onClick={() => setShowAddModal(null)}
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
