import React, { useState, useEffect } from 'react';
import api from '../services/api';
import './KanbanPage.css';

const COLUMNS = [
  { id: 'ideas', title: 'Ideas', color: '#6366f1' },
  { id: 'drafting', title: 'Drafting', color: '#f59e0b' },
  { id: 'review', title: 'In Review', color: '#3b82f6' },
  { id: 'approved', title: 'Approved', color: '#10b981' },
  { id: 'published', title: 'Published', color: '#8b5cf6' }
];

const KanbanPage = ({ organizationId, campaignId }) => {
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [draggedCard, setDraggedCard] = useState(null);
  const [showNewCardModal, setShowNewCardModal] = useState(false);
  const [newCardColumn, setNewCardColumn] = useState(null);

  // Fetch deliverables/tasks as cards
  useEffect(() => {
    const fetchCards = async () => {
      try {
        setLoading(true);
        // Fetch deliverables for the campaign
        const deliverables = await api.listDeliverables(campaignId);
        // Map deliverables to kanban cards
        const kanbanCards = (deliverables || []).map(d => ({
          id: d.id,
          title: d.title,
          content: d.content?.substring(0, 100) + '...',
          type: d.type,
          status: mapStatusToColumn(d.status),
          platform: d.platform,
          createdAt: d.created_at,
          assignee: d.assignee
        }));
        setCards(kanbanCards);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (campaignId) {
      fetchCards();
    }
  }, [campaignId]);

  // Map deliverable status to kanban column
  const mapStatusToColumn = (status) => {
    const statusMap = {
      'draft': 'ideas',
      'in_progress': 'drafting',
      'pending_review': 'review',
      'approved': 'approved',
      'published': 'published'
    };
    return statusMap[status] || 'ideas';
  };

  // Map kanban column to deliverable status
  const mapColumnToStatus = (column) => {
    const columnMap = {
      'ideas': 'draft',
      'drafting': 'in_progress',
      'review': 'pending_review',
      'approved': 'approved',
      'published': 'published'
    };
    return columnMap[column] || 'draft';
  };

  // Get cards for a specific column
  const getCardsForColumn = (columnId) => {
    return cards.filter(card => card.status === columnId);
  };

  // Handle drag start
  const handleDragStart = (e, card) => {
    setDraggedCard(card);
    e.dataTransfer.effectAllowed = 'move';
  };

  // Handle drag over
  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  // Handle drop
  const handleDrop = async (e, columnId) => {
    e.preventDefault();
    
    if (!draggedCard || draggedCard.status === columnId) {
      setDraggedCard(null);
      return;
    }

    // Optimistic update
    const updatedCards = cards.map(card =>
      card.id === draggedCard.id ? { ...card, status: columnId } : card
    );
    setCards(updatedCards);

    try {
      // Update on server
      await api.updateDeliverable(draggedCard.id, {
        status: mapColumnToStatus(columnId)
      });
    } catch (err) {
      // Revert on error
      setCards(cards);
      setError(`Failed to move card: ${err.message}`);
    }

    setDraggedCard(null);
  };

  // Handle new card creation
  const handleCreateCard = async (cardData) => {
    try {
      const newDeliverable = await api.createDeliverable({
        campaign_id: campaignId,
        title: cardData.title,
        content: cardData.content,
        type: cardData.type,
        status: mapColumnToStatus(newCardColumn),
        platform: cardData.platform
      });

      setCards([...cards, {
        id: newDeliverable.id,
        title: newDeliverable.title,
        content: newDeliverable.content?.substring(0, 100) + '...',
        type: newDeliverable.type,
        status: newCardColumn,
        platform: newDeliverable.platform,
        createdAt: newDeliverable.created_at
      }]);

      setShowNewCardModal(false);
      setNewCardColumn(null);
    } catch (err) {
      setError(`Failed to create card: ${err.message}`);
    }
  };

  // Render a single card
  const renderCard = (card) => (
    <div
      key={card.id}
      className={`kanban-card ${draggedCard?.id === card.id ? 'dragging' : ''}`}
      draggable
      onDragStart={(e) => handleDragStart(e, card)}
    >
      <div className="card-header">
        <span className={`card-type ${card.type}`}>{card.type}</span>
        {card.platform && (
          <span className={`card-platform ${card.platform}`}>{card.platform}</span>
        )}
      </div>
      <h4 className="card-title">{card.title}</h4>
      <p className="card-content">{card.content}</p>
      <div className="card-footer">
        {card.assignee && (
          <span className="card-assignee">{card.assignee}</span>
        )}
        <span className="card-date">
          {new Date(card.createdAt).toLocaleDateString()}
        </span>
      </div>
    </div>
  );

  // Render a column
  const renderColumn = (column) => {
    const columnCards = getCardsForColumn(column.id);
    
    return (
      <div
        key={column.id}
        className="kanban-column"
        onDragOver={handleDragOver}
        onDrop={(e) => handleDrop(e, column.id)}
      >
        <div className="column-header" style={{ borderTopColor: column.color }}>
          <h3>{column.title}</h3>
          <span className="card-count">{columnCards.length}</span>
        </div>
        
        <div className="column-content">
          {columnCards.map(card => renderCard(card))}
        </div>
        
        <button
          className="add-card-btn"
          onClick={() => {
            setNewCardColumn(column.id);
            setShowNewCardModal(true);
          }}
        >
          + Add Card
        </button>
      </div>
    );
  };

  // New card modal
  const renderNewCardModal = () => {
    if (!showNewCardModal) return null;

    return (
      <div className="modal-overlay" onClick={() => setShowNewCardModal(false)}>
        <div className="modal-content" onClick={e => e.stopPropagation()}>
          <h3>New Card</h3>
          <form onSubmit={(e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            handleCreateCard({
              title: formData.get('title'),
              content: formData.get('content'),
              type: formData.get('type'),
              platform: formData.get('platform')
            });
          }}>
            <div className="form-group">
              <label>Title</label>
              <input name="title" required />
            </div>
            <div className="form-group">
              <label>Content</label>
              <textarea name="content" rows={4} />
            </div>
            <div className="form-group">
              <label>Type</label>
              <select name="type">
                <option value="social">Social Post</option>
                <option value="blog">Blog Article</option>
                <option value="email">Email</option>
                <option value="ad">Advertisement</option>
              </select>
            </div>
            <div className="form-group">
              <label>Platform</label>
              <select name="platform">
                <option value="">None</option>
                <option value="twitter">Twitter</option>
                <option value="linkedin">LinkedIn</option>
                <option value="instagram">Instagram</option>
                <option value="facebook">Facebook</option>
              </select>
            </div>
            <div className="modal-actions">
              <button type="button" onClick={() => setShowNewCardModal(false)}>Cancel</button>
              <button type="submit" className="primary">Create</button>
            </div>
          </form>
        </div>
      </div>
    );
  };

  if (!campaignId) {
    return (
      <div className="kanban-page">
        <div className="no-campaign">
          <h2>Select a Campaign</h2>
          <p>Please select a campaign to view its content board.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="kanban-page">
      <div className="kanban-header">
        <h1>Content Board</h1>
        {error && <div className="error-banner">{error}</div>}
      </div>

      {loading ? (
        <div className="loading">Loading board...</div>
      ) : (
        <div className="kanban-board">
          {COLUMNS.map(column => renderColumn(column))}
        </div>
      )}

      {renderNewCardModal()}
    </div>
  );
};

export default KanbanPage;
